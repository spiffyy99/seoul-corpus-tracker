import json
import re
from pathlib import Path

from kiwipiepy import Kiwi
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent
TRANSCRIPTS_DIR = ROOT / "transcripts"
OUTPUT_BASE = ROOT / "dist" / "transcripts_json"

CORPUS_DIRS = {
    "conversational-speech-corpus": "conversational_speech_corpus",
    "spontaneous-speech-corpus": "spontaneous_speech_corpus",
}

# Kiwi with the same custom rules used for the seoul corpus
kiwi = Kiwi()
rules = {
    "계세요": [("계시", "VV", 0, 2), ("세요", "EF", 1, 3)],
    "드세요": [("드시", "VV", 0, 2), ("세요", "EF", 1, 3)],
    "주무세요": [("주무시", "VV", 0, 3), ("세요", "EF", 2, 4)],
    "잡수세요": [("잡수시", "VV", 0, 2), ("세요", "EF", 2, 4)],
}
for form, analyzed in rules.items():
    kiwi.add_pre_analyzed_word(form, analyzed, score=100)

LINE_RE = re.compile(
    r"^\[(\d+\.?\d*),(\d+\.?\d*)\]\s+(\S+)\s+(\S+)\s+(.*)$"
)


def parse_line(line):
    m = LINE_RE.match(line.strip())
    if not m:
        return None
    return {
        "start": float(m.group(1)),
        "end": float(m.group(2)),
        "speaker": m.group(3),
        "gender": m.group(4),
        "text": m.group(5).strip(),
    }


def analyze_morphology(text):
    tokens = kiwi.tokenize(text, normalize_coda=True)
    return [[t.form, t.tag, t.start, t.len] for t in tokens]


def convert_corpus(corpus_dir_name, output_subdir):
    src_dir = TRANSCRIPTS_DIR / corpus_dir_name
    out_dir = OUTPUT_BASE / output_subdir
    out_dir.mkdir(parents=True, exist_ok=True)

    txt_files = sorted(
        p for p in src_dir.iterdir()
        if p.is_file() and p.suffix.lower() == ".txt"
    )

    success = 0
    failed = 0

    for src in txt_files:
        dst = out_dir / f"{src.stem}.json"
        try:
            entries = []
            max_end = 0.0
            with open(src, "r", encoding="utf-8") as f:
                for line in f:
                    parsed = parse_line(line)
                    if not parsed:
                        continue
                    max_end = max(max_end, parsed["end"])
                    entries.append(parsed)

            # Build utterance array: [text, morphology, start, end]
            # No word-level timestamps in these corpora, so wordSpans is omitted.
            # parseEntry() falls back to explicit start/end when wordSpans is absent.
            utterances = []
            for e in entries:
                utterances.append([
                    e["text"],
                    analyze_morphology(e["text"]),
                    e["start"],
                    e["end"],
                ])

            data = {
                "length": max_end,
                "utterances": utterances,
            }

            with open(dst, "w", encoding="utf-8", newline="\n") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
                f.write("\n")

            success += 1
            print(f"  Converted: {src.name} -> {dst.name} ({len(utterances)} utterances, length={max_end:.2f}s)")

        except Exception as e:
            failed += 1
            print(f"  FAILED: {src.name}: {e}")

    print(f"\n  {corpus_dir_name}: {success} converted, {failed} failed")
    return success, failed


def main():
    print("Conversational & spontaneous speech corpora → transcript JSON\n")
    total_ok = 0
    total_fail = 0
    for corpus, subdir in CORPUS_DIRS.items():
        print(f"=== {corpus} ===")
        ok, fail = convert_corpus(corpus, subdir)
        total_ok += ok
        total_fail += fail

    print(f"\nDone. Total: {total_ok} converted, {total_fail} failed")


if __name__ == "__main__":
    main()