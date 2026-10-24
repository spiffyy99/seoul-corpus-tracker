#!/usr/bin/env python3
"""
Compare Kiwi spacing settings on Korean utterances.

Usage:
    python test_kiwi_spacing.py
    python test_kiwi_spacing.py --input utterances.txt
    python test_kiwi_spacing.py --input utterances.txt --output spacing_results.csv
    python test_kiwi_spacing.py --include-combinations

Input format:
    UTF-8 text file, one utterance per line. Blank lines are ignored.
    If no --input is supplied, a few diagnostic examples are used.

The script compares:
  - space_tolerance: 0, 1, 2 (with the default space_penalty)
  - space_penalty: 3, 5, 7, 10 (with the default space_tolerance)
  - optionally, a small grid of combined settings
  - reset_whitespace=False and True

It writes every output to CSV so you can compare settings side by side.
"""

import argparse
import csv
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

try:
    from kiwipiepy import Kiwi
    import kiwipiepy
except ImportError:
    print(
        "Could not import kiwipiepy. Install it with:\n"
        "    python -m pip install -U kiwipiepy",
        file=sys.stderr,
    )
    raise SystemExit(1)


DEFAULT_CASES = [
    {
        "text": "밤에 서 계속 놀았어요",
        "expected": "밤에서 계속 놀았어요",
        "note": "Known spacing correction to preserve",
    },
    {
        "text": "사시고계세요",
        "expected": "사시고 계세요",
        "note": "Missing space between the verb and auxiliary construction",
    },
    {
        "text": "사시고 계세요",
        "expected": "사시고 계세요",
        "note": "Already-correct spacing should ideally survive",
    },
    {
        "text": "오늘은 날씨가 정말 좋았어요",
        "expected": "오늘은 날씨가 정말 좋았어요",
        "note": "Ordinary correctly spaced control",
    },
    {
        "text": "저는학교에갔다가친구를만났어요",
        "expected": "저는 학교에 갔다가 친구를 만났어요",
        "note": "Several missing spaces",
    },
    {
        "text": "띄 어 쓰 기 문 제 가 있 습 니 다",
        "expected": "띄어쓰기 문제가 있습니다",
        "note": "Kiwi documentation-style spacing stress test",
    },
]


def read_inputs(path):
    """Read one utterance per line, or use built-in examples."""
    if path is None:
        return DEFAULT_CASES

    lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
    cases = []
    for line_number, line in enumerate(lines, start=1):
        text = line.strip()
        if not text:
            continue
        cases.append({
            "text": text,
            "expected": "",
            "note": f"Input line {line_number}",
        })
    if not cases:
        raise ValueError(f"No nonblank utterances found in {path}")
    return cases


def build_configurations(include_combinations=False):
    """Return named, isolated settings to test."""
    configs = [
        ("baseline", 0, 7.0),
        ("tolerance_1", 1, 7.0),
        ("tolerance_2", 2, 7.0),
        ("penalty_3", 0, 3.0),
        ("penalty_5", 0, 5.0),
        ("penalty_10", 0, 10.0),
    ]
    if include_combinations:
        for tolerance in (1, 2):
            for penalty in (3.0, 5.0, 10.0):
                configs.append(
                    (f"tol{tolerance}_penalty{penalty:g}", tolerance, penalty)
                )
    return configs


def analyze_one(text, tolerance, penalty, reset_whitespace):
    """Create a fresh Kiwi instance for each setting, then space the text."""
    kiwi = Kiwi()
    kiwi.space_tolerance = tolerance
    kiwi.space_penalty = penalty
    output = kiwi.space(text, reset_whitespace=reset_whitespace)

    # Include a compact morphology diagnostic for the most important case.
    tokens = kiwi.tokenize(text)
    morphology = " ".join(f"{token.form}/{token.tag}" for token in tokens)
    return output, morphology


def main():
    parser = argparse.ArgumentParser(
        description="Compare Kiwi spacing parameters on Korean utterances."
    )
    parser.add_argument(
        "--input",
        help="Optional UTF-8 text file: one Korean utterance per line.",
    )
    parser.add_argument(
        "--output",
        default="spacing_results.csv",
        help="CSV output path (default: spacing_results.csv).",
    )
    parser.add_argument(
        "--include-combinations",
        action="store_true",
        help="Also test combinations of tolerance and penalty settings.",
    )
    parser.add_argument(
        "--show-morphology",
        action="store_true",
        help="Print Kiwi tokenization for each original input.",
    )
    args = parser.parse_args()

    cases = read_inputs(args.input)
    configs = build_configurations(args.include_combinations)

    print(f"kiwipiepy version: {getattr(kiwipiepy, '__version__', 'unknown')}")
    print(f"Utterances: {len(cases)}")
    print(f"Configurations: {len(configs)}")
    print("Each configuration is tested with reset_whitespace=False and True.")
    print()

    rows = []
    for case_index, case in enumerate(cases, start=1):
        original = case["text"]
        expected = case["expected"]
        print(f"[{case_index}/{len(cases)}] INPUT:    {original}")
        if expected:
            print(f"             EXPECTED: {expected}")
        if case["note"]:
            print(f"             NOTE:     {case['note']}")

        for name, tolerance, penalty in configs:
            for reset in (False, True):
                output, morphology = analyze_one(
                    original, tolerance, penalty, reset
                )
                rows.append({
                    "case_number": case_index,
                    "input": original,
                    "expected": expected,
                    "configuration": name,
                    "space_tolerance": tolerance,
                    "space_penalty": penalty,
                    "reset_whitespace": reset,
                    "output": output,
                    "matches_expected": (
                        output == expected if expected else ""
                    ),
                    "note": case["note"],
                    "morphology": morphology,
                })
                print(
                    f"  {name:16s} reset={str(reset):5s} -> {output}"
                )

        if args.show_morphology:
            # The baseline morphology is the diagnostic of the original input.
            _, morphology = analyze_one(original, 0, 7.0, False)
            print(f"  TOKENS: {morphology}")
        print()

    output_path = Path(args.output)
    fieldnames = [
        "case_number",
        "input",
        "expected",
        "configuration",
        "space_tolerance",
        "space_penalty",
        "reset_whitespace",
        "output",
        "matches_expected",
        "note",
        "morphology",
    ]
    with output_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved detailed results to: {output_path.resolve()}")
    print(
        "\nHow to use this:\n"
        "- First run the built-in cases and inspect the differences.\n"
        "- Then pass your representative utterance list with --input.\n"
        "- Do not choose a setting from just one example; check whether it "
        "fixes errors without breaking already-correct spacing.\n"
        "- If all settings produce the same output for a case, the parameters "
        "probably aren't addressing that particular failure."
    )


if __name__ == "__main__":
    main()
