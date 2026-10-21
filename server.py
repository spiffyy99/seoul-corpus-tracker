from __future__ import annotations
from flask import Flask, request, send_from_directory
import os
from pathlib import Path

app = Flask(__name__, static_folder='dist')
clip_info = None


def set_clip_info(clip_info_impl):
    global clip_info
    clip_info = clip_info_impl


@app.get("/api/clips/<clip_name>/play")
def play_sound(clip_name: str):
    try:
        audio, length = clip_info.get_clip_sound(clip_name)
    except FileNotFoundError:
        return app.response_class(
            "Audio clip not found.",
            status=404,
            mimetype="text/plain",
        )
    except Exception:
        app.logger.exception("Could not load audio clip %s", clip_name)
        return app.response_class(
            "Audio clip is temporarily unavailable.",
            status=503,
            mimetype="text/plain",
        )

    headers = {
        "Accept-Ranges": "bytes",
        "Cache-Control": "public, max-age=31536000, immutable",
    }
    status_code = 200

    range_header = request.headers.get("Range")
    if range_header:
        try:
            unit, values = range_header.split("=", 1)
            if unit != "bytes" or "," in values:
                raise ValueError("Only a single byte range is supported")
            first, last = values.split("-", 1)
            if first:
                start = int(first)
                end = int(last) if last else length - 1
            else:
                suffix_length = int(last)
                if suffix_length <= 0:
                    raise ValueError("Invalid suffix range")
                start = max(0, length - suffix_length)
                end = length - 1
            if start < 0 or start >= length or end < start:
                raise ValueError("Range is outside the clip")
            end = min(end, length - 1)
        except (ValueError, TypeError):
            return app.response_class(
                status=416,
                headers={
                    **headers,
                    "Content-Range": f"bytes */{length}",
                },
            )

        audio = audio[start : end + 1]
        headers["Content-Range"] = f"bytes {start}-{end}/{length}"
        status_code = 206

    response = app.response_class(
        audio,
        status=status_code,
        mimetype="audio/ogg; codecs=opus",
        headers=headers,
    )
    response.content_length = len(audio)
    return response


@app.get("/")
def index():
    return send_from_directory('dist', 'index.html')


@app.get("/<path:path>")
def static_files(path):
    return send_from_directory('dist', path)

