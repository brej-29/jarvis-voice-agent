"""
Download the DeepPavlov/clinc_oos intent dataset from Hugging Face Datasets.

This script is optional and intended to support the EDA notebook. When offline
or when the datasets library is not available, the notebook can still run
using data/sample_intents.csv.
"""

from __future__ import annotations

from pathlib import Path

from datasets import load_dataset  # type: ignore[import]


def main() -> None:
    dataset = load_dataset("DeepPavlov/clinc_oos")

    output_dir = Path("data")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "clinc_oos_intents.csv"

    rows: list[dict[str, str]] = []

    for split in ("train", "validation", "test"):
        ds_split = dataset[split]
        for row in ds_split:
            rows.append(
                {
                    "text": row["text"],
                    "intent": row["intent"],
                    "split": split,
                }
            )

    import csv

    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["text", "intent", "split"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {output_path}")


if __name__ == "__main__":
    main()