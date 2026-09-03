"""生成4x4 AlphaZero训练前后对比用的真实对局日志。"""

import json
import random
from pathlib import Path

import numpy as np
import torch

from alphazero_core import (
    AlphaZeroNet,
    get_loaded_model,
    load_model,
    neural_mcts_policy,
    tactical_move,
)
from board_environment import new_board, terminal
from multiboard_tournament import rollout_mcts_move


PROJECT_ROOT = Path(__file__).resolve().parent
SHOWCASE_DIR = PROJECT_ROOT / "logs" / "alphazero" / "showcase" / "4x4"


def training_games_at(iteration):
    path = PROJECT_ROOT / "logs" / "alphazero" / "training_4x4.jsonl"
    if not path.exists():
        return 0
    total = 0
    with open(path, encoding="utf-8") as file:
        for line in file:
            item = json.loads(line)
            if item["iteration"] <= iteration:
                total += item["games"]
    return total


def play_game(model, device, phase, training_games, alpha_simulations, mcts_simulations, seed):
    python_rng = random.Random(seed)
    numpy_rng = np.random.default_rng(seed)
    board = new_board(4)
    mark = "X"
    events = []
    while True:
        if mark == "X":
            forced = tactical_move(board, mark, 4, 4)
            if forced is not None:
                move = forced
            else:
                policy = neural_mcts_policy(
                    board,
                    mark,
                    model,
                    device,
                    size=4,
                    win_length=4,
                    simulations=alpha_simulations,
                    temperature=0.0,
                    rng=numpy_rng,
                )
                legal = [index for index, cell in enumerate(board) if cell == " "]
                move = max(legal, key=lambda item: float(policy[item]))
            strategy = "alpha_zero"
        else:
            move = rollout_mcts_move(
                board, mark, 4, 4, mcts_simulations, python_rng
            )
            strategy = "mcts"

        board[move] = mark
        events.append(
            {
                "phase": phase,
                "training_games": training_games,
                "mark": mark,
                "strategy": strategy,
                "move": move,
                "board": board.copy(),
            }
        )
        finished, result = terminal(board, size=4, win_length=4)
        if finished:
            return events, result
        mark = "O" if mark == "X" else "X"


def save_log(path, events, result, phase, training_games, seed, mcts_simulations):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        for event in events:
            file.write(json.dumps(event, ensure_ascii=False) + "\n")
        file.write(
            json.dumps(
                {
                    "performative": "GAME_OVER",
                    "result": result,
                    "phase": phase,
                    "training_games": training_games,
                    "seed": seed,
                    "mcts_simulations": mcts_simulations,
                },
                ensure_ascii=False,
            )
            + "\n"
        )


def find_game(model, device, phase, training_games, alpha_simulations, mcts_simulations, wanted, start_seed):
    for seed in range(start_seed, start_seed + 100):
        events, result = play_game(
            model,
            device,
            phase,
            training_games,
            alpha_simulations,
            mcts_simulations,
            seed,
        )
        alpha_result = (
            "DRAW" if result == "DRAW" else "WIN" if result == "X" else "LOSS"
        )
        if alpha_result == wanted:
            return events, result, seed
    raise RuntimeError(f"没有找到phase={phase}的目标对局")


def main():
    SHOWCASE_DIR.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    early_model = AlphaZeroNet(channels=8, blocks=1).to(device).eval()
    early_events, early_result, early_seed = find_game(
        early_model,
        device,
        "before_training",
        0,
        alpha_simulations=10,
        mcts_simulations=1,
        wanted="LOSS",
        start_seed=1201,
    )
    save_log(
        SHOWCASE_DIR / "01_before_training_loss.jsonl",
        early_events,
        early_result,
        "before_training",
        0,
        early_seed,
        1,
    )

    middle_checkpoint = (
        PROJECT_ROOT / "models" / "alphazero" / "alphazero_4x4_best.pt"
    )
    middle_model, middle_device, _ = load_model(middle_checkpoint, device=device)
    middle_games = training_games_at(12)
    middle_events, middle_result, middle_seed = find_game(
        middle_model,
        middle_device,
        "mid_training",
        middle_games,
        alpha_simulations=50,
        mcts_simulations=1,
        wanted="DRAW",
        start_seed=1701,
    )
    save_log(
        SHOWCASE_DIR / "02_mid_training_draw.jsonl",
        middle_events,
        middle_result,
        "mid_training",
        middle_games,
        middle_seed,
        1,
    )

    trained_model, trained_device = get_loaded_model(4)
    late_games = training_games_at(16)
    late_events, late_result, late_seed = find_game(
        trained_model,
        trained_device,
        "after_training",
        late_games,
        alpha_simulations=50,
        mcts_simulations=1,
        wanted="WIN",
        start_seed=2201,
    )
    save_log(
        SHOWCASE_DIR / "03_after_training_win.jsonl",
        late_events,
        late_result,
        "after_training",
        late_games,
        late_seed,
        1,
    )
    print(f"before_training: {early_result}, seed={early_seed}")
    print(f"after_training: {late_result}, seed={late_seed}, self_play_games={late_games}")
    print(f"日志目录：{SHOWCASE_DIR}")


if __name__ == "__main__":
    main()
