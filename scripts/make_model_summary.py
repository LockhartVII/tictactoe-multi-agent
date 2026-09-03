"""绘制各棋盘尺寸的最佳模型、训练量和 tournament 汇总图。"""

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
SIZES = (3, 4, 5, 9)


def read_json_lines(path):
    if not path.exists():
        return []
    rows = []
    with open(path, encoding="utf-8") as file:
        for line in file:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def load_data():
    data = []
    for size in SIZES:
        training = read_json_lines(
            PROJECT_ROOT / "logs" / "alphazero" / f"training_{size}x{size}.jsonl"
        )
        selection_path = (
            PROJECT_ROOT
            / "evaluation"
            / "results"
            / f"alphazero_selection_{size}x{size}.json"
        )
        selection = {}
        if selection_path.exists():
            with open(selection_path, encoding="utf-8") as file:
                selection = json.load(file)
        if not selection:
            valid = [row for row in training if "loss" in row]
            best = min(valid, key=lambda row: row["loss"]) if valid else {}
            selection = {
                "iteration": best.get("iteration"),
                "loss": best.get("loss"),
            }
        tournament_path = (
            PROJECT_ROOT
            / "evaluation"
            / "results"
            / (
                "strategy_tournament.json"
                if size == 3
                else f"multiboard_{size}x{size}.json"
            )
        )
        tournament = []
        if tournament_path.exists():
            with open(tournament_path, encoding="utf-8") as file:
                tournament = json.load(file)
        alpha_row = next(
            (row for row in tournament if row.get("strategy") == "alpha_zero"),
            {},
        )
        data.append(
            {
                "size": size,
                "games": sum(row.get("games", 0) for row in training),
                "loss": selection.get("loss"),
                "iteration": selection.get("iteration"),
                "points": alpha_row.get("points", 0),
                "rank": alpha_row.get("rank", "-"),
            }
        )
    return data


def main():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = load_data()
    labels = [f"{row['size']}x{row['size']}" for row in rows]
    figure, axes = plt.subplots(2, 2, figsize=(12, 8))
    figure.suptitle("Best AlphaZero Checkpoints", fontsize=16)

    axes[0, 0].bar(labels, [row["games"] for row in rows], color="#d95f59")
    axes[0, 0].set_title("Logged self-play games")
    axes[0, 0].set_ylabel("Games")

    losses = [row["loss"] or 0 for row in rows]
    axes[0, 1].bar(labels, losses, color="#4f83cc")
    axes[0, 1].set_title("Selected checkpoint loss")
    axes[0, 1].set_ylabel("Loss")

    axes[1, 0].bar(labels, [row["points"] for row in rows], color="#55a868")
    axes[1, 0].set_title("AlphaZero tournament points")
    axes[1, 0].set_ylabel("Points")

    axes[1, 1].axis("off")
    summary = "\n".join(
        f"{row['size']}x{row['size']}: iter {row['iteration']}, rank {row['rank']}"
        for row in rows
    )
    axes[1, 1].text(
        0.05,
        0.75,
        "Selected models\n\n" + summary,
        fontsize=13,
        va="top",
    )
    figure.tight_layout()
    output = PROJECT_ROOT / "evaluation" / "figures" / "alphazero_best_models.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=180, bbox_inches="tight")
    plt.close(figure)
    print(f"图片：{output}")
    for row in rows:
        print(row)


if __name__ == "__main__":
    main()
