
import json
from pathlib import Path

SOURCE_DIR = Path("transcripts_json")
OUTPUT_DIR = Path("transcripts_compact")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    original_total = 0
    compact_total = 0
    processed = 0
    errors = []

    for source_path in sorted(SOURCE_DIR.glob("*.json")):
        try:
            original_size = source_path.stat().st_size

            with source_path.open("r", encoding="utf-8") as f:
                data = json.load(f)

            # Tier 3 is the Hangul pronunciation utterance tier.
            entries = data["tiers"][3]["entries"]

            # Preserve each entry's timestamps and text.
            compact_data = {"length": data["xmax"], "utterances": entries}

            output_path = OUTPUT_DIR / source_path.name
            with output_path.open("w", encoding="utf-8") as f:
                json.dump(
                    compact_data,
                    f,
                    ensure_ascii=False,
                    indent=2
                )

            compact_size = output_path.stat().st_size

            original_total += original_size
            compact_total += compact_size
            processed += 1

        except (OSError, json.JSONDecodeError, KeyError, IndexError, TypeError) as e:
            errors.append(f"{source_path.name}: {e}")

    print(f"Processed: {processed} files")
    print(f"Original total: {original_total / 1_000_000:.2f} MB")
    print(f"Compact total:  {compact_total / 1_000_000:.2f} MB")

    if original_total:
        reduction = (1 - compact_total / original_total) * 100
        print(f"Size reduction: {reduction:.1f}%")

    if errors:
        print(f"\nFailed: {len(errors)} files")
        for error in errors:
            print(f"  {error}")


if __name__ == "__main__":
    main()
