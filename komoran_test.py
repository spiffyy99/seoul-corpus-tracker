import re
import sys
from pathlib import Path

from PyKomoran import Komoran

sys.stdout.reconfigure(encoding="utf-8")

INPUT_FILE = Path("kiwi_test.txt")
OUTPUT_FILE = Path("komoran_test.txt")

# Supports:
# [95] 319.65s–323.08s: 아 베이비시터가 ...
# [1] 네
HEADER_RE = re.compile(r"^\[(\d+)\]\s+(.*)$")


def extract_text(header_content: str) -> str:
    # Remove the timestamp prefix if this is a timestamped header.
    match = re.match(r"^.*?s[–—-].*?s:\s*(.*)$", header_content)
    return match.group(1) if match else header_content


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Could not find {INPUT_FILE.resolve()}")

    print("Initializing KOMORAN...", flush=True)
    komoran = Komoran("EXP")

    output = []
    current_count = 0

    for line in INPUT_FILE.read_text(encoding="utf-8").splitlines():
        match = HEADER_RE.match(line)
        if not match:
            continue

        utterance_id, header_content = match.groups()
        text = extract_text(header_content)

        # Skip empty utterances.
        if not text.strip():
            continue

        current_count += 1
        output.append(f"[{utterance_id}] {text}")

        try:
            analysis = komoran.get_plain_text(text)
            output.append(f"  {analysis}")
        except Exception as exc:
            output.append(f"  ANALYSIS ERROR: {exc}")

        output.append("")

        if current_count % 25 == 0:
            print(f"Analyzed {current_count} utterances...", flush=True)

    OUTPUT_FILE.write_text("\n".join(output), encoding="utf-8")
    print(f"Analyzed {current_count} utterances.")
    print(f"Output: {OUTPUT_FILE.resolve()}")


if __name__ == "__main__":
    main()