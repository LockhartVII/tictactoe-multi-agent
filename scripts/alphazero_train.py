"""训练完整 AlphaZero：自我对弈、回放池和 policy/value 更新。"""

import argparse
import json
import random
from collections import deque
from pathlib import Path

import numpy as np
import torch

from alphazero_core import (
    AlphaZeroNet,
    encode_board,
    neural_mcts_policy,
    other_mark,
)
from board_environment import new_board, terminal, winner


PROJECT_ROOT = Path(__file__).resolve().parent


def augment_sample(state, policy, size):
    state = state.reshape(size, size)
    policy = policy.reshape(size, size)
    samples = []
    for rotations in range(4):
        rotated_state = np.rot90(state, rotations)
        rotated_policy = np.rot90(policy, rotations)
        samples.append(
            (
                np.ascontiguousarray(rotated_state),
                np.ascontiguousarray(rotated_policy).reshape(size * size),
            )
        )
        samples.append(
            (
                np.ascontiguousarray(np.fliplr(rotated_state)),
                np.ascontiguousarray(np.fliplr(rotated_policy)).reshape(size * size),
            )
        )
    return samples


def self_play_game(model, device, size, win_length, simulations, rng, temperature_moves):
    board = new_board(size)
    mark = "X"
    move_number = 0
    records = []
    trajectory = []

    while True:
        temperature = 1.0 if move_number < temperature_moves else 0.1
        policy = neural_mcts_policy(
            board,
            mark,
            model,
            device,
            size=size,
            win_length=win_length,
            simulations=simulations,
            temperature=temperature,
            add_noise=True,
            rng=rng,
        )
        records.append((encode_board(board, mark, size), policy, mark))

        move = int(rng.choice(size * size, p=policy))
        trajectory.append(
            {
                "move_number": move_number + 1,
                "mark": mark,
                "board_before": board.copy(),
                "move": move,
                "policy": policy.tolist(),
                "temperature": temperature,
            }
        )
        board[move] = mark
        trajectory[-1]["board_after"] = board.copy()
        finished, result = terminal(board, size=size, win_length=win_length)
        if finished:
            samples = []
            for state, action_policy, side in records:
                if result == "DRAW":
                    value = 0.0
                elif result == side:
                    value = 1.0
                else:
                    value = -1.0
                for augmented_state, augmented_policy in augment_sample(
                    state, action_policy, size
                ):
                    samples.append((augmented_state, augmented_policy, value))
            for event in trajectory:
                event["result"] = result
            return samples, result, move_number + 1, trajectory

        mark = other_mark(mark)
        move_number += 1


def train_on_replay(model, device, replay, optimizer, size, epochs, batch_size):
    if len(replay) < 2:
        return 0.0, 0.0, 0.0

    model.train()
    examples = list(replay)
    total_loss = 0.0
    total_policy_loss = 0.0
    total_value_loss = 0.0
    batches = 0

    for _ in range(epochs):
        random.shuffle(examples)
        for start in range(0, len(examples), batch_size):
            batch = examples[start : start + batch_size]
            if len(batch) < 2:
                continue
            states, policies, values = zip(*batch)
            state_tensor = torch.from_numpy(np.stack(states)).to(device)
            state_tensor = state_tensor.unsqueeze(1)
            policy_target = torch.from_numpy(np.stack(policies)).to(device)
            value_target = torch.tensor(values, dtype=torch.float32, device=device)

            optimizer.zero_grad()
            policy_logits, value_prediction = model(state_tensor)
            policy_loss = -(
                policy_target * torch.log_softmax(policy_logits, dim=1)
            ).sum(dim=1).mean()
            value_loss = torch.nn.functional.mse_loss(
                value_prediction.squeeze(1), value_target
            )
            loss = policy_loss + value_loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            optimizer.step()

            total_loss += float(loss.item())
            total_policy_loss += float(policy_loss.item())
            total_value_loss += float(value_loss.item())
            batches += 1

    model.eval()
    if batches == 0:
        return 0.0, 0.0, 0.0
    return (
        total_loss / batches,
        total_policy_loss / batches,
        total_value_loss / batches,
    )


def save_replay(replay, size):
    replay_dir = PROJECT_ROOT / "data" / "self_play" / f"{size}x{size}"
    replay_dir.mkdir(parents=True, exist_ok=True)
    path = replay_dir / "replay_latest.npz"
    states, policies, values = zip(*replay)
    np.savez_compressed(
        path,
        states=np.stack(states),
        policies=np.stack(policies),
        values=np.asarray(values, dtype=np.float32),
    )
    return path


def save_self_play_log(trajectory, size, iteration, game_number, result):
    log_dir = (
        PROJECT_ROOT
        / "logs"
        / "alphazero"
        / "self_play"
        / f"{size}x{size}"
        / f"iteration_{iteration:03d}"
    )
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / f"game_{game_number:03d}.jsonl"
    with open(path, "w", encoding="utf-8") as file:
        for event in trajectory:
            file.write(json.dumps(event, ensure_ascii=False) + "\n")
        file.write(
            json.dumps(
                {
                    "performative": "GAME_OVER",
                    "result": result,
                    "size": size,
                },
                ensure_ascii=False,
            )
            + "\n"
        )
    return path


def save_checkpoint(model, optimizer, path, size, win_length, channels, blocks, iteration):
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "model_config": {
                "size": size,
                "win_length": win_length,
                "channels": channels,
                "blocks": blocks,
            },
            "iteration": iteration,
        },
        path,
    )


def train(args):
    if args.win_length is None:
        args.win_length = min(args.size, 5)
    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if device.type == "cuda":
        torch.cuda.manual_seed_all(args.seed)

    model = AlphaZeroNet(channels=args.channels, blocks=args.blocks).to(device)
    optimizer = torch.optim.Adam(
        model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay
    )
    checkpoint = Path(args.checkpoint) if args.checkpoint else (
        PROJECT_ROOT
        / "models"
        / "alphazero"
        / f"alphazero_{args.size}x{args.size}_best.pt"
    )
    start_iteration = 1
    if args.resume and checkpoint.exists():
        saved = torch.load(checkpoint, map_location=device, weights_only=False)
        model.load_state_dict(saved["model_state_dict"])
        optimizer.load_state_dict(saved["optimizer_state_dict"])
        start_iteration = int(saved.get("iteration", 0)) + 1

    model.eval()
    replay = deque(maxlen=args.replay_size)
    rng = np.random.default_rng(args.seed)
    log_dir = PROJECT_ROOT / "logs" / "alphazero"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"training_{args.size}x{args.size}.jsonl"
    replay_path = PROJECT_ROOT / "data" / "self_play" / f"{args.size}x{args.size}" / "replay_latest.npz"
    if args.resume and replay_path.exists():
        saved_replay = np.load(replay_path)
        replay.extend(
            zip(
                saved_replay["states"],
                saved_replay["policies"],
                saved_replay["values"].tolist(),
            )
        )

    print(
        f"AlphaZero训练：{args.size}x{args.size}，胜利长度={args.win_length}，"
        f"device={device}"
    )
    with open(log_path, "a", encoding="utf-8") as log_file:
        for iteration in range(start_iteration, args.iterations + 1):
            wins = {"X": 0, "O": 0, "DRAW": 0}
            move_lengths = []
            iteration_samples = []
            for game_number in range(1, args.games_per_iteration + 1):
                samples, result, move_count, trajectory = self_play_game(
                    model,
                    device,
                    args.size,
                    args.win_length,
                    args.simulations,
                    rng,
                    args.temperature_moves,
                )
                replay.extend(samples)
                iteration_samples.extend(samples)
                save_self_play_log(
                    trajectory,
                    args.size,
                    iteration,
                    game_number,
                    result,
                )
                wins[result] += 1
                move_lengths.append(move_count)

            loss, policy_loss, value_loss = train_on_replay(
                model,
                device,
                replay,
                optimizer,
                args.size,
                args.epochs,
                args.batch_size,
            )
            save_checkpoint(
                model,
                optimizer,
                checkpoint,
                args.size,
                args.win_length,
                args.channels,
                args.blocks,
                iteration,
            )
            candidate_checkpoint = checkpoint.with_name(
                f"{checkpoint.stem}_iter_{iteration:03d}.pt"
            )
            save_checkpoint(
                model,
                optimizer,
                candidate_checkpoint,
                args.size,
                args.win_length,
                args.channels,
                args.blocks,
                iteration,
            )
            replay_path = save_replay(replay, args.size)
            record = {
                "iteration": iteration,
                "size": args.size,
                "games": args.games_per_iteration,
                "simulations": args.simulations,
                "replay_size": len(replay),
                "new_samples": len(iteration_samples),
                "wins": wins,
                "average_moves": sum(move_lengths) / len(move_lengths),
                "loss": loss,
                "policy_loss": policy_loss,
                "value_loss": value_loss,
                "checkpoint": str(checkpoint),
                "candidate_checkpoint": str(candidate_checkpoint),
            }
            log_file.write(json.dumps(record, ensure_ascii=False) + "\n")
            log_file.flush()
            print(
                f"iter {iteration}/{args.iterations} | "
                f"X/DRAW/O={wins['X']}/{wins['DRAW']}/{wins['O']} | "
                f"replay={len(replay)} | loss={loss:.4f}"
            )

    print(f"模型：{checkpoint}")
    print(f"训练日志：{log_path}")
    print(f"回放数据：{replay_path}")


def main():
    parser = argparse.ArgumentParser(description="训练可配置棋盘尺寸的完整AlphaZero")
    parser.add_argument("--size", type=int, required=True, choices=(3, 4, 5, 9))
    parser.add_argument("--win-length", type=int, default=None)
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument("--games-per-iteration", type=int, default=20)
    parser.add_argument("--simulations", type=int, default=50)
    parser.add_argument("--temperature-moves", type=int, default=4)
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--replay-size", type=int, default=50000)
    parser.add_argument("--channels", type=int, default=32)
    parser.add_argument("--blocks", type=int, default=2)
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--checkpoint", default=None)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    train(args)


if __name__ == "__main__":
    main()
