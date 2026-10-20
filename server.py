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
async def play_sound(clip_name: str):
    audio, length = await clip_info.get_clip_sound(clip_name)
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


@app.get("/")
def index():
    return send_from_directory('dist', 'index.html')


@app.get("/<path:path>")
def static_files(path):
    return send_from_directory('dist', path)

