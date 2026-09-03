"""在4x4、5x5和9x9棋盘上比较通用策略与训练后的AlphaZero。"""

import argparse
import csv
import itertools
import json
import random
from pathlib import Path

from alphazero_core import (
    get_loaded_model,
    neural_mcts_policy,
    other_mark,
    tactical_move,
)
from board_environment import available, board_size, new_board, terminal, winner


PROJECT_ROOT = Path(__file__).resolve().parent
STRATEGIES = ("random", "heuristic", "mcts", "alpha_zero")


def _points(result, mark):
    if result == mark:
        return 3
    if result == "DRAW":
        return 1
    return 0


def _winning_move(board, mark, size, win_length):
    for move in available(board):
        trial = board.copy()
        trial[move] = mark
        if winner(trial, size=size, win_length=win_length) == mark:
            return move
    return None


def heuristic_move(board, mark, size, win_length, rng):
    move = _winning_move(board, mark, size, win_length)
    if move is not None:
        return move
    move = _winning_move(board, other_mark(mark), size, win_length)
    if move is not None:
        return move

    center = (size * size) // 2
    if center in available(board):
        return center
    return rng.choice(available(board))


def rollout_mcts_move(board, mark, size, win_length, simulations, rng):
    moves = available(board)
    if not moves:
        return None
    tactical_move = _winning_move(board, mark, size, win_length)
    if tactical_move is not None:
        return tactical_move
    tactical_move = _winning_move(board, other_mark(mark), size, win_length)
    if tactical_move is not None:
        return tactical_move

    scores = {move: 0.0 for move in moves}
    for move in moves:
        for _ in range(max(1, simulations)):
            trial = board.copy()
            trial[move] = mark
            side = other_mark(mark)
            while True:
                finished, result = terminal(
                    trial, size=size, win_length=win_length
                )
                if finished:
                    scores[move] += _points(result, mark)
                    break
                random_move = rng.choice(available(trial))
                trial[random_move] = side
                side = other_mark(side)
    return max(moves, key=lambda move: (scores[move], -move))


def choose_move(
    board,
    mark,
    strategy,
    size,
    win_length,
    simulations,
    rng,
    checkpoint=None,
    alpha_simulations=None,
    baseline_simulations=None,
):
    if strategy == "random":
        return rng.choice(available(board))
    if strategy == "heuristic":
        return heuristic_move(board, mark, size, win_length, rng)
    if strategy == "mcts":
        return rollout_mcts_move(
            board,
            mark,
            size,
            win_length,
            baseline_simulations or simulations,
            rng,
        )
    if strategy == "alpha_zero":
        forced_move = tactical_move(board, mark, size, win_length)
        if forced_move is not None:
            return forced_move
        model, device = get_loaded_model(size, checkpoint=checkpoint)
        policy = neural_mcts_policy(
            board,
            mark,
            model,
            device,
            size=size,
            win_length=win_length,
            simulations=alpha_simulations or simulations,
            temperature=0.0,
        )
        return max(available(board), key=lambda move: float(policy[move]))
    raise ValueError("未知策略：" + strategy)


def play_game(
    x_strategy,
    o_strategy,
    size,
    win_length,
    simulations,
    seed,
    log_path,
    checkpoint=None,
    alpha_simulations=None,
    baseline_simulations=None,
):
    rng = random.Random(seed)
    board = new_board(size)
    mark = "X"
    strategies = {"X": x_strategy, "O": o_strategy}
    messages = []

    while True:
        strategy = strategies[mark]
        move = choose_move(
            board,
            mark,
            strategy,
            size,
            win_length,
            simulations,
            rng,
            checkpoint=checkpoint,
            alpha_simulations=alpha_simulations,
            baseline_simulations=baseline_simulations,
        )
        board[move] = mark
        messages.append(
            {
                "mark": mark,
                "strategy": strategy,
                "move": move,
                "board": board.copy(),
            }
        )
        finished, result = terminal(board, size=size, win_length=win_length)
        if finished:
            break
        mark = other_mark(mark)

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as file:
        for message in messages:
            file.write(json.dumps(message, ensure_ascii=False) + "\n")
        file.write(
            json.dumps(
                {"performative": "GAME_OVER", "result": result},
                ensure_ascii=False,
            )
            + "\n"
        )
    return result, len(messages)


def empty_stats():
    return {
        "games": 0,
        "wins": 0,
        "draws": 0,
        "losses": 0,
        "points": 0,
        "first_games": 0,
        "first_points": 0,
        "second_games": 0,
        "second_points": 0,
    }


def record(stats, x_strategy, o_strategy, result):
    x_stats = stats[x_strategy]
    o_stats = stats[o_strategy]
    x_stats["games"] += 1
    o_stats["games"] += 1
    x_stats["first_games"] += 1
    o_stats["second_games"] += 1
    x_stats["points"] += _points(result, "X")
    o_stats["points"] += _points(result, "O")
    x_stats["first_points"] += _points(result, "X")
    o_stats["second_points"] += _points(result, "O")

    if result == "X":
        x_stats["wins"] += 1
        o_stats["losses"] += 1
    elif result == "O":
        o_stats["wins"] += 1
        x_stats["losses"] += 1
    else:
        x_stats["draws"] += 1
        o_stats["draws"] += 1


def write_results(rows, size):
    directory = PROJECT_ROOT / "evaluation" / "results"
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / f"multiboard_{size}x{size}.json"
    csv_path = directory / f"multiboard_{size}x{size}.csv"
    with open(json_path, "w", encoding="utf-8") as file:
        json.dump(rows, file, ensure_ascii=False, indent=2)
    with open(csv_path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return json_path, csv_path


def draw_chart(rows, size):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    directory = PROJECT_ROOT / "evaluation" / "figures"
    directory.mkdir(parents=True, exist_ok=True)
    figure_path = directory / f"multiboard_{size}x{size}.png"
    names = [row["strategy"] for row in rows]
    positions = list(range(len(names)))
    width = 0.24
    figure, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].bar(
        [position - width for position in positions],
        [row["wins"] for row in rows],
        width,
        label="Wins",
    )
    axes[0].bar(
        positions,
        [row["draws"] for row in rows],
        width,
        label="Draws",
    )
    axes[0].bar(
        [position + width for position in positions],
        [row["losses"] for row in rows],
        width,
        label="Losses",
    )
    axes[0].set_title(f"{size}x{size} Results")
    axes[0].set_ylabel("Games")
    axes[0].set_xticks(positions, names, rotation=30, ha="right")
    axes[0].legend()

    axes[1].bar(
        [position - width / 2 for position in positions],
        [row["first_points"] for row in rows],
        width,
        label="First player",
    )
    axes[1].bar(
        [position + width / 2 for position in positions],
        [row["second_points"] for row in rows],
        width,
        label="Second player",
    )
    axes[1].set_title("First vs Second")
    axes[1].set_ylabel("Points")
    axes[1].set_xticks(positions, names, rotation=30, ha="right")
    axes[1].legend()
    figure.suptitle(f"Strategy Tournament: {size}x{size}")
    figure.tight_layout()
    figure.savefig(figure_path, dpi=160, bbox_inches="tight")
    plt.close(figure)
    return figure_path


def run_tournament(
    size,
    win_length,
    strategies,
    games_per_pair,
    simulations,
    seed,
    checkpoint=None,
    focus_alpha_zero=False,
    alpha_simulations=None,
    baseline_simulations=None,
):
    stats = {strategy: empty_stats() for strategy in strategies}
    log_root = PROJECT_ROOT / "logs" / "multiboard_tournament" / f"{size}x{size}"
    pair_number = 0
    if focus_alpha_zero:
        pairings = [
            ("alpha_zero", strategy)
            for strategy in strategies
            if strategy != "alpha_zero"
        ]
    else:
        pairings = list(itertools.combinations(strategies, 2))
    total_games = len(pairings) * games_per_pair

    for first_strategy, second_strategy in pairings:
        for game_index in range(games_per_pair):
            pair_number += 1
            if game_index % 2 == 0:
                x_strategy, o_strategy = first_strategy, second_strategy
            else:
                x_strategy, o_strategy = second_strategy, first_strategy
            log_path = log_root / (
                f"{first_strategy}_vs_{second_strategy}"
            ) / f"game_{game_index + 1:02d}_{x_strategy}_first.jsonl"
            result, moves = play_game(
                x_strategy,
                o_strategy,
                size,
                win_length,
                simulations,
                seed + pair_number,
                log_path,
                checkpoint=checkpoint,
                alpha_simulations=alpha_simulations,
                baseline_simulations=baseline_simulations,
            )
            record(stats, x_strategy, o_strategy, result)
            print(
                f"[{pair_number}/{total_games}] {x_strategy}先手 vs "
                f"{o_strategy}：{result}，{moves}步"
            )

    rows = [{"strategy": strategy, **values} for strategy, values in stats.items()]
    rows.sort(key=lambda row: (-row["points"], -row["wins"], row["strategy"]))
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    json_path, csv_path = write_results(rows, size)
    figure_path = draw_chart(rows, size)
    print(f"\n{size}x{size} 最佳策略：{rows[0]['strategy']}（{rows[0]['points']}分）")
    print(f"结果 JSON：{json_path}")
    print(f"结果 CSV：{csv_path}")
    print(f"结果图片：{figure_path}")
    return rows


def main():
    parser = argparse.ArgumentParser(description="多棋盘尺寸策略锦标赛")
    parser.add_argument("--size", type=int, required=True, choices=(4, 5, 9))
    parser.add_argument("--win-length", type=int, default=None)
    parser.add_argument(
        "--strategies", nargs="+", choices=STRATEGIES, default=list(STRATEGIES)
    )
    parser.add_argument("--games-per-pair", type=int, default=2)
    parser.add_argument("--simulations", type=int, default=30)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--checkpoint", default=None)
    parser.add_argument("--alpha-simulations", type=int, default=None)
    parser.add_argument("--baseline-simulations", type=int, default=None)
    parser.add_argument(
        "--focus-alpha-zero",
        action="store_true",
        help="只测试AlphaZero与其余策略，减少大棋盘无关对局",
    )
    args = parser.parse_args()
    if args.win_length is None:
        args.win_length = min(args.size, 5)
    if len(set(args.strategies)) < 2:
        parser.error("至少需要两种策略")
    strategies = tuple(dict.fromkeys(args.strategies))
    if args.focus_alpha_zero:
        strategies = ("alpha_zero",) + tuple(
            strategy for strategy in strategies if strategy != "alpha_zero"
        )
    run_tournament(
        args.size,
        args.win_length,
        strategies,
        args.games_per_pair,
        args.simulations,
        args.seed,
        checkpoint=args.checkpoint,
        focus_alpha_zero=args.focus_alpha_zero,
        alpha_simulations=args.alpha_simulations,
        baseline_simulations=args.baseline_simulations,
    )


if __name__ == "__main__":
    main()
