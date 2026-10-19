from __future__ import annotations
from flask import Flask, request

app = Flask(__name__)
clip_info = None


def set_clip_info(clip_info_impl):
    global clip_info
    clip_info = clip_info_impl


@app.get("/api/clips/<clip_name>/play")
def play_sound(clip_name: str):
    audio, length = clip_info.get_clip_sound(clip_name)
    response = app.response_class(
        audio,
        mimetype="audio/webm",
        direct_passthrough=True,
    )
    response.content_length = length
    response.headers["Accept-Ranges"] = "bytes"
    response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    response.call_on_close(audio.close)
    return response

