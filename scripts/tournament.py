import argparse
import csv
import itertools
import json

from main import project_path
from minmax import run_one_game


STRATEGIES = (
    "random",
    "heuristic",
    "minimax",
    "alpha_beta",
    "mcts",
    "alpha_zero",
)


def _empty_stats():
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


def _points(result, mark):
    if result == mark:
        return 3
    if result == "DRAW":
        return 1
    return 0


def _record_result(stats, x_strategy, o_strategy, result):
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


def _write_results(rows):
    result_dir = project_path("evaluation/results")
    result_dir.mkdir(parents=True, exist_ok=True)

    json_path = result_dir / "strategy_tournament.json"
    csv_path = result_dir / "strategy_tournament.csv"
    with open(json_path, "w", encoding="utf-8") as file:
        json.dump(rows, file, ensure_ascii=False, indent=2)

    fields = list(rows[0].keys())
    with open(csv_path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    return json_path, csv_path


def _draw_chart(rows):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure_dir = project_path("evaluation/figures")
    figure_dir.mkdir(parents=True, exist_ok=True)
    figure_path = figure_dir / "strategy_tournament.png"

    names = [row["strategy"] for row in rows]
    positions = list(range(len(names)))
    width = 0.24

    figure, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    axes[0].bar(
        [position - width for position in positions],
        [row["wins"] for row in rows],
        width,
        label="Wins",
        color="#4C78A8",
    )
    axes[0].bar(
        positions,
        [row["draws"] for row in rows],
        width,
        label="Draws",
        color="#F2CF5B",
    )
    axes[0].bar(
        [position + width for position in positions],
        [row["losses"] for row in rows],
        width,
        label="Losses",
        color="#E45756",
    )
    axes[0].set_title("3x3 Results")
    axes[0].set_ylabel("Games")
    axes[0].set_xticks(positions, names, rotation=35, ha="right")
    axes[0].legend()

    axes[1].bar(
        [position - width / 2 for position in positions],
        [row["first_points"] for row in rows],
        width,
        label="First player",
        color="#59A14F",
    )
    axes[1].bar(
        [position + width / 2 for position in positions],
        [row["second_points"] for row in rows],
        width,
        label="Second player",
        color="#B279A2",
    )
    axes[1].set_title("First vs Second")
    axes[1].set_ylabel("Points")
    axes[1].set_xticks(positions, names, rotation=35, ha="right")
    axes[1].legend()

    best = rows[0]
    figure.suptitle(
        f"Strategy Tournament | Best: {best['strategy']} ({best['points']} points)",
        fontsize=14,
    )
    figure.tight_layout()
    figure.savefig(figure_path, dpi=170, bbox_inches="tight")
    plt.close(figure)
    return figure_path


def run_tournament(strategies=STRATEGIES):
    stats = {strategy: _empty_stats() for strategy in strategies}
    match_root = project_path("logs/tournament")

    pairs = list(itertools.combinations(strategies, 2))
    total_games = len(pairs) * 2
    completed_games = 0

    for first_strategy, second_strategy in pairs:
        match_dir = match_root / f"{first_strategy}_vs_{second_strategy}"
        first_log = match_dir / f"game_01_{first_strategy}_first.jsonl"
        second_log = match_dir / f"game_02_{second_strategy}_first.jsonl"

        print(
            f"\n[{completed_games + 1}-{completed_games + 2}/{total_games}] "
            f"{first_strategy} vs {second_strategy}"
        )
        result = run_one_game(
            completed_games + 1,
            player_x_strategy=first_strategy,
            player_o_strategy=second_strategy,
            log_relative_path=str(first_log),
        )
        _record_result(stats, first_strategy, second_strategy, result)
        completed_games += 1
        print(f"  {first_strategy}先手：{result}")

        result = run_one_game(
            completed_games + 1,
            player_x_strategy=second_strategy,
            player_o_strategy=first_strategy,
            log_relative_path=str(second_log),
        )
        _record_result(stats, second_strategy, first_strategy, result)
        completed_games += 1
        print(f"  {second_strategy}先手：{result}")

    rows = []
    for strategy, strategy_stats in stats.items():
        rows.append({"strategy": strategy, **strategy_stats})
    rows.sort(key=lambda row: (-row["points"], -row["wins"], row["strategy"]))
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank

    json_path, csv_path = _write_results(rows)
    figure_path = _draw_chart(rows)

    print("\n策略锦标赛结果（胜=3分，和=1分，负=0分）")
    print("Rank  Strategy     Points  W  D  L  First  Second")
    for row in rows:
        print(
            f"{row['rank']:<5} {row['strategy']:<12} "
            f"{row['points']:<7} {row['wins']:<2} {row['draws']:<2} "
            f"{row['losses']:<2} {row['first_points']:<7} "
            f"{row['second_points']}"
        )

    print(f"\n最佳策略：{rows[0]['strategy']}（{rows[0]['points']} 分）")
    print(f"统计 JSON：{json_path}")
    print(f"统计 CSV：{csv_path}")
    print(f"可视化图片：{figure_path}")
    return rows


def main():
    parser = argparse.ArgumentParser(description="3×3 井字棋策略锦标赛")
    parser.add_argument(
        "--strategies",
        nargs="+",
        choices=STRATEGIES,
        default=list(STRATEGIES),
        help="指定要参加锦标赛的策略，默认全部参加",
    )
    args = parser.parse_args()
    if len(args.strategies) < 2:
        parser.error("至少需要两种策略")
    run_tournament(tuple(dict.fromkeys(args.strategies)))


if __name__ == "__main__":
    main()
