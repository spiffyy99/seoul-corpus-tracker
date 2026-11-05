"""Merge clip metadata into clips.json.

Replaces the flat clips.json (corpus subdir -> list of clip ids) with a map of
corpus subdir -> { clip_id -> metadata }. The seoul corpus metadata is derived
from the clip name (sNNmMMfFF); the conversational and spontaneous corpora carry
their metadata in `dist/Conversational Speech Corpus.txt`.

The `device` field is dropped (not needed by the UI).
"""
import json
import pathlib
import re

DIST = pathlib.Path("dist")


def parse_corpus_text(path: pathlib.Path) -> dict:
    """Return { corpus_header: { clip_id: {topic, gender, age, region} } }."""
    lines = [raw.rstrip("\n") for raw in open(path, "r", encoding="utf-8")]

    def next_nonblank(idx):
        j = idx + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        return lines[j] if j < len(lines) else ""

    blocks = {}
    current_corpus = None
    current_block = []
    for i, line in enumerate(lines):
        if line.strip() and next_nonblank(i).strip() == "Topics":
            if current_corpus is not None:
                blocks[current_corpus] = current_block
            current_corpus = line.strip()
            current_block = []
            continue
        if current_corpus is not None:
            current_block.append(line)
    if current_corpus is not None:
        blocks[current_corpus] = current_block

    result = {}
    for corpus, block_lines in blocks.items():
        section = None
        topics_rows = []
        speaker_rows = []
        for line in block_lines:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped in ("Topics", "Speakers"):
                section = stripped
                continue
            if stripped.upper().startswith("CHANNEL"):
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            if section == "Topics":
                topics_rows.append(parts)
            elif section == "Speakers":
                speaker_rows.append(parts)

        topics = {}
        for row in topics_rows:
            if len(row) < 4:
                continue
            uttrans_id = row[1].strip()
            clip_id = uttrans_id[:-4] if uttrans_id.endswith(".wav") else uttrans_id
            topics[clip_id] = row[3].strip()

        speakers = {}
        for row in speaker_rows:
            if len(row) < 6:
                continue
            speaker_id = row[1].strip()
            gender = row[2].strip().lower()
            if gender in ("m", "male"):
                gender = "male"
            elif gender in ("f", "female"):
                gender = "female"
            speakers[speaker_id] = {
                "gender": gender,
                "age": row[3].strip(),
                "region": row[4].strip(),
            }

        corpus_result = {}
        for clip_id, topic in topics.items():
            m = re.search(r"_G(\d+)$", clip_id)
            speaker_id = f"G{m.group(1)}" if m else None
            speaker = speakers.get(speaker_id, {})
            corpus_result[clip_id] = {
                "topic": topic,
                "gender": speaker.get("gender"),
                "age": speaker.get("age"),
                "region": speaker.get("region"),
            }
        result[corpus] = corpus_result
    return result


def parse_seoul_corpus() -> dict:
    clips_dir = DIST / "transcripts_json" / "seoul_corpus"
    result = {}
    for p in sorted(clips_dir.glob("*.json")):
        clip_id = p.stem
        m = re.fullmatch(r"s(\d{2})([mf])(\d{2})([mf])([1-6])", clip_id)
        if not m:
            continue
        speaker_id, speaker_gender, speaker_age, interviewer_gender, segment = m.groups()
        result[clip_id] = {
            "speaker_id": speaker_id,
            "speaker_gender": "male" if speaker_gender == "m" else "female",
            "speaker_age": int(speaker_age),
            "interviewer_gender": "male" if interviewer_gender == "m" else "female",
            "segment_number": int(segment),
        }
    return result


def main():
    clips = {"seoul_corpus": parse_seoul_corpus()}

    text_path = DIST / "Conversational Speech Corpus.txt"
    if text_path.is_file():
        parsed = parse_corpus_text(text_path)
        header_to_subdir = {
            "Conversational Speech Corpus": "conversational_speech_corpus",
            "Spontaneous Speech Corpus": "spontaneous_speech_corpus",
        }
        for header, subdir in header_to_subdir.items():
            clips[subdir] = parsed.get(header, {})
            print(f"{subdir}: {len(clips[subdir])} clips from {text_path.name}")
    else:
        print(f"no metadata file at {text_path}")

    out = DIST / "clips.json"
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(clips, f, ensure_ascii=False, indent=4)
        f.write("\n")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()