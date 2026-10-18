import json
import re
from pathlib import Path

from praatio import textgrid

INPUT_DIR = Path("transcripts")
OUTPUT_DIR = Path("transcripts_json")

# Original one-based TextGrid tier indices:
# 2 = pword.prono (Hangul)
# 4 = utt.prono (Hangul)
# 5 = pword.ortho (Hangul)
# 7 = utt.ortho (Hangul)
KEEP_TIER_INDICES = {2, 4, 5, 7}

HANGUL_RE = re.compile(r"[\uac00-\ud7a3]")


def contains_hangul(text):
    return bool(HANGUL_RE.search(text or ""))


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    files = sorted(
        path for path in INPUT_DIR.iterdir()
        if path.is_file() and path.suffix.lower() == ".textgrid"
    )

    success = 0
    failed = 0

    for src in files:
        dst = OUTPUT_DIR / f"{src.stem}.json"

        try:
            tg = textgrid.openTextgrid(
                str(src),
                includeEmptyIntervals=True,
                duplicateNamesMode="rename",
            )

            # Save a temporary full conversion so we can filter its tiers.
            temp = OUTPUT_DIR / f"{src.stem}.temp.json"

            tg.save(
                str(temp),
                format="textgrid_json",
                includeBlankSpaces=True,
            )

            with temp.open("r", encoding="utf-8") as f:
                data = json.load(f)

            temp.unlink()

            # Keep selected tiers, filtering by original tier order.
            filtered_tiers = []

            for index, tier in enumerate(data["tiers"], start=1):
                if index not in KEEP_TIER_INDICES:
                    continue

                tier["entries"] = [
                    entry
                    for entry in tier["entries"]
                    if contains_hangul(entry[-1])
                ]

                filtered_tiers.append(tier)

            data["tiers"] = filtered_tiers

            # Write readable JSON and preserve Korean characters.
            with dst.open("w", encoding="utf-8", newline="\n") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.write("\n")

            success += 1
            print(f"Converted: {src.name} -> {dst.name}")

        except Exception as e:
            failed += 1
            print(f"FAILED: {src.name}: {e}")

    print(f"\nFinished. Converted: {success}, Failed: {failed}")


if __name__ == "__main__":
    main()