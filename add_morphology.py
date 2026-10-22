import json
from pathlib import Path
from kiwipiepy import Kiwi
import sys
import re

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Paths
transcripts_dir = Path(__file__).parent / "dist" / "transcripts_json"
output_dir = Path(__file__).parent / "dist" / "transcripts_json_grammar"

# Create output directory
output_dir.mkdir(exist_ok=True)

# Initialize Kiwi with custom rule for 계세요
kiwi = Kiwi()
rules = {
    "계세요": [("계시", "VV", 0,2), ("세요", "EF", 1, 3)],
    "드세요": [("드시", "VV", 0,2), ("세요", "EF",1, 3)],
    "주무세요": [("주무시", "VV", 0,3), ("세요", "EF",2, 4)],
    "잡수세요": [("잡수시", "VV", 0,2), ("세요", "EF",2,4)],
}   

for form, analyzed in rules.items():
    kiwi.add_pre_analyzed_word(form, analyzed, score=100)

print(f"Processing transcripts from: {transcripts_dir}")
print(f"Output directory: {output_dir}")
print()

# Get all JSON files
json_files = sorted(transcripts_dir.glob("*.json"))
print(f"Found {len(json_files)} transcript files")
print()

# Process each file
for i, json_file in enumerate(json_files, start=1):
    print(f"[{i}/{len(json_files)}] Processing {json_file.name}...", flush=True)

    # Read the original transcript
    data = json.loads(json_file.read_text(encoding="utf-8"))
    utterances = data["utterances"]

    # Add morphological analysis to each utterance
    new_utterances = []
    for utterance in utterances:
        start, end, text = utterance

        # Tokenize the text
        tokens = kiwi.tokenize(text, normalize_coda=True)

        # Convert to array format: [form, tag, start, len]
        morphemes = [
            [token.form, token.tag, token.start, token.len]
            for token in tokens
        ]

        # Create new utterance with morphology as 4th element
        new_utterance = [start, end, text, morphemes]
        new_utterances.append(new_utterance)

    # Create new data structure
    new_data = {
        "length": data["length"],
        "utterances": new_utterances
    }

    # Write to output directory
    output_file = output_dir / json_file.name
    txt = json.dumps(new_data, ensure_ascii=False, indent=4)
    txt = re.sub(
        r'\[\s*(.*?)\s*\]', 
        lambda m: '[' + re.sub(r'\s*\n\s*', ' ', m.group(1)) + ']', 
        txt, 
        flags=re.DOTALL
    )
    output_file.write_text(
        txt.replace("[ [ ", "\n            [ \n                ["),
        encoding="utf-8"
    )

print()
print(f"Done! Processed {len(json_files)} files.")
print(f"Output saved to: {output_dir}")
