"""按训练日志中的最低 loss 挑出一个 AlphaZero checkpoint。"""

import argparse
import json
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description="按训练loss挑选AlphaZero checkpoint")
    parser.add_argument("--size", type=int, required=True, choices=(4, 5, 9))
    args = parser.parse_args()

    model_dir = PROJECT_ROOT / "models" / "alphazero"
    final_checkpoint = model_dir / f"alphazero_{args.size}x{args.size}.pt"
    training_log = PROJECT_ROOT / "logs" / "alphazero" / f"training_{args.size}x{args.size}.jsonl"
    records = []
    if training_log.exists():
        with open(training_log, encoding="utf-8") as file:
            for line in file:
                record = json.loads(line)
                candidate_text = record.get("candidate_checkpoint")
                candidate = Path(candidate_text) if candidate_text else None
                if candidate is not None and candidate.exists() and "loss" in record:
                    records.append(record)
    if records:
        selected_record = min(records, key=lambda record: record["loss"])
        selected = Path(selected_record["candidate_checkpoint"])
    else:
        candidates = sorted(model_dir.glob(f"alphazero_{args.size}x{args.size}_iter_*.pt"))
        if not candidates:
            raise FileNotFoundError(f"没有找到{args.size}x{args.size}的checkpoint")
        selected_record = {"iteration": None, "loss": None}
        selected = candidates[-1]
    shutil.copy2(selected, final_checkpoint)
    output_dir = PROJECT_ROOT / "evaluation" / "results"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"alphazero_selection_{args.size}x{args.size}.json"
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(
            {
                "size": args.size,
                "selection": "training_loss_minimum",
                "iteration": selected_record["iteration"],
                "loss": selected_record["loss"],
                "selected_checkpoint": str(final_checkpoint),
                "source_checkpoint": str(selected),
            },
            file,
            ensure_ascii=False,
            indent=2,
        )
    print(
        f"按训练loss选中：{selected.name}"
        f"（iteration={selected_record['iteration']}，loss={selected_record['loss']}）"
    )
    print(f"复制为正式模型：{final_checkpoint.name}")
    print(f"筛选结果：{output_path}")


if __name__ == "__main__":
    main()
