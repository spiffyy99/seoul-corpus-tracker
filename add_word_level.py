import json
import re
from pathlib import Path

from praatio import textgrid

INPUT_JSON_DIR = Path("dist/transcripts_json")
INPUT_TEXTGRID_DIR = Path("transcripts")

HANGUL_RE = re.compile(r"[\uac00-\ud7a3]")


def contains_hangul(text):
    return text is not None and bool(HANGUL_RE.search(str(text)))


def fmt_num(n):
    f = float(n)
    if f == int(f):
        return str(int(f))
    return repr(f)


def format_morpheme(m):
    return f'["{m[0]}", "{m[1]}", {fmt_num(m[2])}, {fmt_num(m[3])}]'


def format_utterance(u, is_first, is_last):
    text, morphology, word_spans = u
    has_words = bool(word_spans)
    text_str = text if text else ""
    lines = []

    if is_first:
        # First utterance: combined with "utterances": [ prefix -> "[[ text,..."
        lines.append(f"[[ \"{text_str}\", ")
    else:
        # Subsequent utterances: "[ text..." indented 8 spaces
        lines.append(f"        [ \"{text_str}\", ")

    # Morphology array opening
    lines.append("            [ ")
    for m in morphology:
        lines.append(f"                {format_morpheme(m)},")
    if morphology:
        lines[-1] = lines[-1].rstrip(",")

    # Morphology closing: comma if word spans follow
    morph_closer = "            ]," if has_words else "            ]"
    lines.append(morph_closer)

    # Word spans: [[s1, e1], [s2, e2], ...]
    if has_words:
        spans_str = ", ".join(f"[{fmt_num(s)}, {fmt_num(e)}]" for s, e in word_spans)
        lines.append(f"            [{spans_str}]")
    else:
        lines.append("            []")

    # Utterance closing
    closer = "        ]" if is_last else "        ],"
    lines.append(closer)
    return lines


def main():
    tg_cache = {}
    for src in sorted(INPUT_TEXTGRID_DIR.iterdir()):
        if not (src.is_file() and src.suffix.lower() == ".textgrid"):
            continue
        stem = src.stem
        try:
            tg = textgrid.openTextgrid(
                str(src),
                includeEmptyIntervals=True,
                duplicateNamesMode="rename",
            )
            word_tier = tg.getTier("pWord.ortho.")
            tg_cache[stem] = word_tier
        except Exception as e:
            print(f"SKIP (textgrid read failed): {src.name}: {e}")
            tg_cache[stem] = None

    json_files = sorted(INPUT_JSON_DIR.glob("*.json"))
    updated = 0
    skipped = 0

    for jf in json_files:
        stem = jf.stem
        word_tier = tg_cache.get(stem)
        if word_tier is None:
            skipped += 1
            continue

        try:
            with open(str(jf), "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"SKIP (json read failed): {jf.name}: {e}")
            skipped += 1
            continue

        utterances = data.get("utterances", [])
        if not utterances:
            skipped += 1
            continue

        # Word-tier entries containing Hangul, sorted by start time
        word_entries = sorted(
            [w for w in word_tier.entries if contains_hangul(w.label)],
            key=lambda w: w.start,
        )

        new_utterances = []
        for u in utterances:
            start, end, text = u[0], u[1], u[2]
            morphology = u[3] if len(u) > 3 else []

            # Only add word spans for utterances containing Hangul
            if contains_hangul(text):
                word_spans = []
                for w in word_entries:
                    if w.start >= start - 0.001 and w.end <= end + 0.001:
                        word_spans.append([w.start, w.end])
            else:
                word_spans = []

            new_utterances.append([text, morphology, word_spans])

        data["utterances"] = new_utterances

        # Build output matching original format (4-space base indent)
        out_lines = ["{"]
        out_lines.append(f'    "length": {fmt_num(data["length"])},')
        out_lines.append('    "utterances": ')

        for i, u in enumerate(new_utterances):
            is_first = i == 0
            is_last = i == len(new_utterances) - 1
            utt_lines = format_utterance(u, is_first, is_last)
            if i == 0:
                # Merge first utterance line with "utterances": [ prefix
                out_lines[-1] = out_lines[-1] + utt_lines[0]
                out_lines.extend(utt_lines[1:])
            else:
                out_lines.extend(utt_lines)

        out_lines.append("    ]")
        out_lines.append("}")

        content = "\n".join(out_lines) + "\n"

        with open(str(jf), "w", encoding="utf-8") as f:
            f.write(content)

        updated += 1
        print(f"Updated: {jf.name} ({len(utterances)} utterances)")

    print(f"\nDone. Updated: {updated}, Skipped: {skipped}")


if __name__ == "__main__":
    main()
