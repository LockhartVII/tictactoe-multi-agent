"""把 AlphaZero 对局日志画成简洁的蜡笔风格 GIF。"""

import argparse
import json
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parent


def load_font(size):
    candidates = (
        Path("C:/Windows/Fonts/seguisb.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    )
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def draw_crayon_line(draw, start, end, color, width, rng):
    for offset in range(4):
        jittered_start = (
            start[0] + rng.randint(-2, 2),
            start[1] + rng.randint(-2, 2),
        )
        jittered_end = (
            end[0] + rng.randint(-2, 2),
            end[1] + rng.randint(-2, 2),
        )
        draw.line(
            (jittered_start, jittered_end),
            fill=color,
            width=max(2, width - offset),
        )


def draw_mark(draw, mark, row, column, cell, left, top, rng):
    center_x = left + column * cell + cell // 2
    center_y = top + row * cell + cell // 2
    margin = int(cell * 0.23)
    if mark == "X":
        draw_crayon_line(
            draw,
            (center_x - margin, center_y - margin),
            (center_x + margin, center_y + margin),
            "#e34242",
            8,
            rng,
        )
        draw_crayon_line(
            draw,
            (center_x + margin, center_y - margin),
            (center_x - margin, center_y + margin),
            "#e34242",
            8,
            rng,
        )
    elif mark == "O":
        box = (
            center_x - margin,
            center_y - margin,
            center_x + margin,
            center_y + margin,
        )
        for offset in range(4):
            draw.ellipse(
                (
                    box[0] + rng.randint(-2, 2),
                    box[1] + rng.randint(-2, 2),
                    box[2] + rng.randint(-2, 2),
                    box[3] + rng.randint(-2, 2),
                ),
                outline="#2774c6",
                width=max(2, 8 - offset),
            )


def showcase_logs():
    progression_dir = PROJECT_ROOT / "logs" / "alphazero" / "showcase" / "4x4"
    logs = sorted(progression_dir.glob("*.jsonl"))
    if not logs:
        logs = sorted(
            (PROJECT_ROOT / "logs" / "multiboard_tournament" / "4x4").glob(
                "**/*.jsonl"
            )
        )
    selected = []
    for path in logs:
        events, result, alpha_result, opponent, training_games, phase = load_events(path)
        is_progression = "showcase" in path.parts
        if events and (is_progression or alpha_result == "WIN"):
            selected.append(
                (
                    len(events),
                    path,
                    events,
                    result,
                    opponent,
                    training_games,
                    phase,
                    alpha_result,
                )
            )
    selected.sort(key=lambda item: (item[6] != "before_training", item[0], str(item[1])))
    if not selected:
        raise FileNotFoundError("没有找到4x4 AlphaZero获胜日志")
    return selected


def load_events(path):
    events = []
    result = "?"
    alpha_mark = None
    opponent = "unknown"
    training_games = 0
    phase = "tournament"
    with open(path, encoding="utf-8") as file:
        for line in file:
            item = json.loads(line)
            if item.get("performative") == "GAME_OVER":
                result = item.get("result", "?")
                training_games = item.get("training_games", 0)
                phase = item.get("phase", phase)
            elif "board" in item:
                events.append(item)
                training_games = item.get("training_games", training_games)
                phase = item.get("phase", phase)
                if item.get("strategy") == "alpha_zero":
                    alpha_mark = item.get("mark")
                elif item.get("strategy"):
                    opponent = item["strategy"]
    alpha_result = "DRAW" if result == "DRAW" else (
        "WIN" if result == alpha_mark else "LOSS"
    )
    return events, result, alpha_result, opponent, training_games, phase


def make_background(args):
    image = Image.new("RGB", (720, 820), "#fffdf8")
    draw = ImageDraw.Draw(image)
    title_font = load_font(30)
    info_font = load_font(19)
    small_font = load_font(17)
    draw.text((42, 24), "AlphaZero 4x4 showcase", fill="#202020", font=title_font)
    draw.text(
        (44, 70),
        "Model: alphazero_4x4_best.pt   Board: 4x4   Win: 4",
        fill="#555555",
        font=info_font,
    )
    left, top, cell = 80, 155, 140
    right, bottom = left + 4 * cell, top + 4 * cell
    grid_rng = random.Random(2025)
    for index in range(5):
        x = left + index * cell
        draw_crayon_line(draw, (x, top), (x, bottom), "#202020", 5, grid_rng)
        y = top + index * cell
        draw_crayon_line(draw, (left, y), (right, y), "#202020", 5, grid_rng)
    draw.text(
        (44, 101),
        f"Red: AlphaZero   Blue: MCTS   MCTS sims: {args.mcts_simulations}",
        fill="#555555",
        font=info_font,
    )
    draw.text(
        (44, 740),
        "Red X: AlphaZero    Blue O: MCTS",
        fill="#666666",
        font=small_font,
    )
    return image


def make_frame(
    background,
    board_image,
    step,
    total_steps,
    training_games,
    phase,
):
    size = 4
    image = board_image.copy()
    draw = ImageDraw.Draw(image)
    info_font = load_font(19)
    draw.text(
        (44, 126),
        f"Self-play: {training_games:04d}   Phase: {phase}   "
        f"Step: {step}/{total_steps}",
        fill="#555555",
        font=info_font,
    )
    return image


def main():
    parser = argparse.ArgumentParser(description="制作4x4 AlphaZero蜡笔风格GIF")
    parser.add_argument("--log", type=Path, default=None)
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "evaluation" / "figures" / "alphazero_4x4_showcase.gif",
    )
    parser.add_argument("--simulations", type=int, default=30)
    parser.add_argument("--alpha-simulations", type=int, default=50)
    parser.add_argument("--mcts-simulations", type=int, default=1)
    parser.add_argument("--game-number", type=int, default=1)
    parser.add_argument("--games-to-show", type=int, default=12)
    parser.add_argument("--total-games", type=int, default=100)
    parser.add_argument("--duration", type=int, default=520)
    args = parser.parse_args()
    if args.log:
        events, result, alpha_result, opponent, training_games, phase = load_events(args.log)
        candidates = [
            (
                len(events),
                args.log,
                events,
                result,
                opponent,
                training_games,
                phase,
                alpha_result,
            )
        ]
    else:
        candidates = showcase_logs()
    if not candidates or not candidates[0][2]:
        raise ValueError("日志没有可用落子记录")

    rng = random.Random(2026)
    frames = []
    durations = []
    selected_logs = []
    background = make_background(args)
    for display_index in range(args.games_to_show):
        (
            _,
            log_path,
            events,
            result,
            opponent,
            training_games,
            phase,
            alpha_result,
        ) = candidates[display_index % len(candidates)]
        selected_logs.append(str(log_path))
        board_image = background.copy()
        frames.append(
            make_frame(
                background,
                board_image,
                0,
                len(events),
                training_games,
                phase,
            )
        )
        durations.append(170)
        for step in range(1, len(events) + 1):
            move = events[step - 1]["move"]
            mark = events[step - 1]["mark"]
            draw = ImageDraw.Draw(board_image)
            draw_mark(draw, mark, move // 4, move % 4, 140, 80, 155, rng)
            frames.append(
                make_frame(
                    background,
                    board_image,
                    step,
                    len(events),
                    training_games,
                    phase,
                )
            )
            durations.append(105)
        frames.append(
            make_frame(
                background,
                board_image,
                len(events),
                len(events),
                training_games,
                phase,
            )
        )
        durations.append(150)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        args.output,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=False,
    )
    print(f"GIF：{args.output}")
    print(f"精选日志：{len(set(selected_logs))}份，动画对局：{args.games_to_show}局")
    print(f"帧数：{len(frames)}，结果：{result}")


if __name__ == "__main__":
    main()
