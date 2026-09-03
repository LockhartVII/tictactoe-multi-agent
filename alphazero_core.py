"""可配置棋盘尺寸的完整 AlphaZero 核心：网络、神经 MCTS 和模型加载。"""

from pathlib import Path

import numpy as np
import torch
from torch import nn

from board_environment import (
    available,
    board_size,
    empty,
    terminal,
    winner,
    winner_from_move,
)


PROJECT_ROOT = Path(__file__).resolve().parent
_loaded_models = {}


def other_mark(mark):
    return "O" if mark == "X" else "X"


def encode_board(board, mark, size=None):
    if size is None:
        size = board_size(board)
    encoded = np.zeros((size, size), dtype=np.float32)
    for index, cell in enumerate(board):
        if cell == mark:
            encoded[index // size, index % size] = 1.0
        elif cell != empty:
            encoded[index // size, index % size] = -1.0
    return encoded


class ResidualBlock(nn.Module):
    def __init__(self, channels):
        super().__init__()
        self.conv1 = nn.Conv2d(channels, channels, 3, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(channels)
        self.conv2 = nn.Conv2d(channels, channels, 3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(channels)

    def forward(self, x):
        residual = x
        x = torch.relu(self.bn1(self.conv1(x)))
        x = self.bn2(self.conv2(x))
        return torch.relu(x + residual)


class AlphaZeroNet(nn.Module):
    """全卷积 policy/value 网络，棋盘尺寸由输入决定。"""

    def __init__(self, channels=64, blocks=3):
        super().__init__()
        self.stem = nn.Sequential(
            nn.Conv2d(1, channels, 3, padding=1, bias=False),
            nn.BatchNorm2d(channels),
            nn.ReLU(),
        )
        self.residual_tower = nn.Sequential(
            *(ResidualBlock(channels) for _ in range(blocks))
        )
        self.policy_head = nn.Sequential(
            nn.Conv2d(channels, 2, 1),
            nn.ReLU(),
            nn.Conv2d(2, 1, 1),
            nn.Flatten(),
        )
        self.value_head = nn.Sequential(
            nn.Conv2d(channels, 1, 1),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(1, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Tanh(),
        )

    def forward(self, x):
        x = self.stem(x)
        x = self.residual_tower(x)
        return self.policy_head(x), self.value_head(x)


def checkpoint_path(size):
    return PROJECT_ROOT / "models" / "alphazero" / f"alphazero_{size}x{size}.pt"


def load_model(checkpoint, device=None):
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint = Path(checkpoint)
    if not checkpoint.exists():
        raise FileNotFoundError(f"未找到完整AlphaZero模型：{checkpoint}")

    saved = torch.load(checkpoint, map_location=device, weights_only=False)
    if "model_state_dict" in saved:
        model_config = saved.get("model_config", {})
        channels = model_config.get("channels", 64)
        blocks = model_config.get("blocks", 3)
        size = model_config.get("size")
    else:
        model_config = {}
        channels = 64
        blocks = 3
        size = None
    model = AlphaZeroNet(channels=channels, blocks=blocks)
    model.load_state_dict(saved.get("model_state_dict", saved))
    model.to(device).eval()
    return model, device, size


def get_loaded_model(size, checkpoint=None):
    if checkpoint is None:
        checkpoint = checkpoint_path(size)
    checkpoint = Path(checkpoint)
    key = str(checkpoint.resolve())
    if key not in _loaded_models:
        _loaded_models[key] = load_model(checkpoint)
    model, device, saved_size = _loaded_models[key]
    if saved_size is not None and saved_size != size:
        raise ValueError(f"模型适用于{saved_size}x{saved_size}，当前棋盘是{size}x{size}")
    return model, device


class SearchNode:
    def __init__(
        self, board, to_move, prior=0.0, parent=None, move=None, last_move=None
    ):
        self.board = board
        self.to_move = to_move
        self.prior = float(prior)
        self.parent = parent
        self.move = move
        self.last_move = last_move
        self.children = []
        self.visits = 0
        self.value_sum = 0.0


def _terminal_value(board, to_move, size, win_length, last_move=None):
    if last_move is None:
        result = winner(board, size=size, win_length=win_length)
    else:
        result = winner_from_move(
            board, last_move, size=size, win_length=win_length
        )
    if result is None and not available(board):
        return 0.0
    if result is None:
        return None
    if result == "DRAW":
        return 0.0
    return 1.0 if result == to_move else -1.0


def _evaluate(model, device, board, to_move, size):
    encoded = encode_board(board, to_move, size=size)
    tensor = torch.from_numpy(encoded).to(device).reshape(1, 1, size, size)
    with torch.no_grad():
        policy_logits, value = model(tensor)
    return (
        torch.softmax(policy_logits, dim=1)[0].cpu().numpy(),
        float(value.item()),
    )


def _put_mark(board, move, mark):
    trial = board.copy()
    trial[move] = mark
    return trial


def tactical_move(board, mark, size, win_length):
    """处理一步之内能直接结束棋局的着法，减少搜索的低级漏算。"""
    legal_moves = available(board)
    opponent = other_mark(mark)
    for candidate_mark in (mark, opponent):
        for move in legal_moves:
            trial = _put_mark(board, move, candidate_mark)
            if winner(trial, size=size, win_length=win_length) == candidate_mark:
                return move
    return None


def _expand(node, policy):
    legal_moves = available(node.board)
    priors = np.array([max(0.0, float(policy[move])) for move in legal_moves])
    if priors.sum() <= 0:
        priors = np.ones(len(legal_moves), dtype=np.float32)
    priors /= priors.sum()
    node.children = [
        SearchNode(
            board=_put_mark(node.board, move, node.to_move),
            to_move=other_mark(node.to_move),
            prior=prior,
            parent=node,
            move=move,
            last_move=move,
        )
        for move, prior in zip(legal_moves, priors)
    ]


def _select_child(node, c_puct):
    parent_visits = max(1, node.visits)

    def score(child):
        q_value = 0.0
        if child.visits:
            q_value = -child.value_sum / child.visits
        exploration = c_puct * child.prior * np.sqrt(parent_visits) / (1 + child.visits)
        return q_value + exploration

    return max(node.children, key=score)


def neural_mcts_policy(
    board,
    mark,
    model,
    device,
    size=None,
    win_length=None,
    simulations=100,
    temperature=1.0,
    add_noise=False,
    rng=None,
    c_puct=1.5,
):
    """用 policy/value 网络引导 MCTS，返回每个位置的搜索概率。"""
    if size is None:
        size = board_size(board)
    if win_length is None:
        win_length = min(size, 5)
    legal_moves = available(board)
    if not legal_moves:
        return np.zeros(size * size, dtype=np.float32)
    if rng is None:
        rng = np.random.default_rng()

    root = SearchNode(board.copy(), mark)
    root_policy, _ = _evaluate(model, device, root.board, root.to_move, size)
    _expand(root, root_policy)

    if add_noise and root.children:
        noise = rng.dirichlet(np.full(len(root.children), 0.3))
        for child, noise_value in zip(root.children, noise):
            child.prior = 0.75 * child.prior + 0.25 * float(noise_value)

    for _ in range(max(1, simulations)):
        node = root
        while node.children and _terminal_value(
            node.board, node.to_move, size, win_length, node.last_move
        ) is None:
            node = _select_child(node, c_puct)

        value = _terminal_value(
            node.board, node.to_move, size, win_length, node.last_move
        )
        if value is None:
            policy, value = _evaluate(model, device, node.board, node.to_move, size)
            _expand(node, policy)

        while node is not None:
            node.visits += 1
            node.value_sum += value
            value = -value
            node = node.parent

    counts = np.zeros(size * size, dtype=np.float32)
    for child in root.children:
        counts[child.move] = child.visits
    if counts.sum() == 0:
        counts[legal_moves[0]] = 1.0

    if temperature <= 1e-6:
        policy = np.zeros(size * size, dtype=np.float32)
        policy[max(legal_moves, key=lambda move: counts[move])] = 1.0
        return policy

    adjusted = counts ** (1.0 / temperature)
    adjusted[[index for index in range(size * size) if index not in legal_moves]] = 0
    total = adjusted.sum()
    return adjusted / total if total > 0 else counts / counts.sum()


def full_alphazero_move(board, mark, size=None, win_length=None, simulations=200):
    if size is None:
        size = board_size(board)
    if win_length is None:
        win_length = min(size, 5)
    forced_move = tactical_move(board, mark, size, win_length)
    if forced_move is not None:
        return forced_move
    model, device = get_loaded_model(size)
    policy = neural_mcts_policy(
        board,
        mark,
        model,
        device,
        size=size,
        win_length=win_length,
        simulations=simulations,
        temperature=0.0,
    )
    return max(available(board), key=lambda move: float(policy[move]))
