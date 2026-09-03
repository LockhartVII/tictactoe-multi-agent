import math
import random

from environment import available, terminal, winner, empty


def _other_mark(mark):
    return "O" if mark == "X" else "X"


def alpha_beta(board, current_mark, maximizing_mark, alpha=-2, beta=2):
    """Alpha-Beta版本的Minimax，返回maximizing_mark视角下的分数。"""
    finished, result = terminal(board)
    if finished:
        if result == maximizing_mark:
            return 1
        if result == "DRAW":
            return 0
        return -1

    next_mark = _other_mark(current_mark)

    if current_mark == maximizing_mark:
        best_score = -2
        for move in available(board):
            trial = board.copy()
            trial[move] = current_mark
            score = alpha_beta(
                trial, next_mark, maximizing_mark, alpha, beta
            )
            best_score = max(best_score, score)
            alpha = max(alpha, best_score)
            if beta <= alpha:
                break
        return best_score

    best_score = 2
    for move in available(board):
        trial = board.copy()
        trial[move] = current_mark
        score = alpha_beta(
            trial, next_mark, maximizing_mark, alpha, beta
        )
        best_score = min(best_score, score)
        beta = min(beta, best_score)
        if beta <= alpha:
            break
    return best_score


def _preferred_moves(board):
    order = [4, 0, 2, 6, 8, 1, 3, 5, 7]
    return [move for move in order if move in available(board)]


def alpha_beta_move(board, mark):
    """选择Alpha-Beta搜索评分最高的合法动作。"""
    best_move = None
    best_score = -2

    for move in _preferred_moves(board):
        trial = board.copy()
        trial[move] = mark
        score = alpha_beta(
            trial,
            _other_mark(mark),
            mark
        )
        if score > best_score:
            best_score = score
            best_move = move

    return best_move


class MCTSNode:
    def __init__(self, board, to_move, parent=None, move=None):
        self.board = board
        self.to_move = to_move
        self.parent = parent
        self.move = move
        self.children = []
        self.untried_moves = available(board)
        self.visits = 0
        self.value = 0.0


def _result_value(result, root_mark):
    if result == root_mark:
        return 1.0
    if result == "DRAW":
        return 0.0
    return -1.0


def _rollout(board, to_move, root_mark, rng):
    trial = board.copy()
    mark = to_move

    while True:
        finished, result = terminal(trial)
        if finished:
            return _result_value(result, root_mark)

        move = rng.choice(available(trial))
        trial[move] = mark
        mark = _other_mark(mark)


def _select_child(node, root_mark):
    log_visits = math.log(max(1, node.visits))

    def uct_score(child):
        if child.visits == 0:
            return float("inf")

        average = child.value / child.visits
        # 对手回合希望让root玩家的分数变低。
        if node.to_move != root_mark:
            average = -average

        exploration = math.sqrt(2.0 * log_visits / child.visits)
        return average + exploration

    return max(node.children, key=uct_score)


def mcts_move(board, mark, simulations=500, seed=None):
    """使用UCT进行推理，并保留简单的立即获胜/阻挡检查。"""
    moves = available(board)
    if not moves:
        return None

    # 先处理两个最重要的战术动作，减少随机模拟漏掉直接胜负的情况。
    for move in moves:
        trial = board.copy()
        trial[move] = mark
        if winner(trial) == mark:
            return move

    opponent = _other_mark(mark)
    for move in moves:
        trial = board.copy()
        trial[move] = opponent
        if winner(trial) == opponent:
            return move

    rng = random.Random(seed)
    root = MCTSNode(board.copy(), mark)

    for _ in range(simulations):
        node = root

        # Selection
        while not terminal(node.board)[0]:
            if node.untried_moves:
                break
            node = _select_child(node, mark)

        # Expansion
        if not terminal(node.board)[0] and node.untried_moves:
            move = rng.choice(node.untried_moves)
            node.untried_moves.remove(move)
            trial = node.board.copy()
            trial[move] = node.to_move
            child = MCTSNode(
                trial,
                _other_mark(node.to_move),
                parent=node,
                move=move
            )
            node.children.append(child)
            node = child

        # Simulation
        finished, result = terminal(node.board)
        if finished:
            value = _result_value(result, mark)
        else:
            value = _rollout(node.board, node.to_move, mark, rng)

        # Backpropagation
        while node is not None:
            node.visits += 1
            node.value += value
            node = node.parent

    if not root.children:
        return moves[0]

    preferred = {move: index for index, move in enumerate(_preferred_moves(board))}
    best_child = max(
        root.children,
        key=lambda child: (
            child.visits,
            child.value / child.visits if child.visits else -2,
            -preferred.get(child.move, 99)
        )
    )
    return best_child.move


def alpha_zero_move(board, mark):
    """调用可选的AlphaZero模型；模型不可用时退回MCTS。"""
    try:
        from alphazero_adapter import model_move
        return model_move(board, mark)
    except Exception:
        # 预训练权重或TensorFlow不可用时，仍然保持Agent可运行。
        return mcts_move(board, mark, simulations=800)


def choose_move(board, mark, strategy):
    """统一策略入口，方便Player Agent继续使用原消息协议。"""
    if strategy == "alpha_beta":
        return alpha_beta_move(board, mark)
    if strategy == "mcts":
        return mcts_move(board, mark)
    if strategy in ("alpha_zero", "alphazero"):
        return alpha_zero_move(board, mark)
    raise ValueError("未知的策略：" + strategy)
