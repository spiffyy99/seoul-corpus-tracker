from __future__ import annotations
from flask import Flask, jsonify, request, send_file
from typing import BinaryIO
from local_clip_info import LocalClipInfo

app = Flask(__name__)
clip_info = LocalClipInfo()

@app.route("/api/clips")
def clips():
    return jsonify(clip_info.get_clip_names())

@app.route("/api/clips/<clip_name>/utterances")
def utterances(clip_name: str):
    return jsonify(clip_info.get_utterances(clip_name))

@app.get("/api/clips/<clip_name>/play")
def play_sound(clip_name: str):
    audio, length = clip_info.get_clip_sound(clip_name)
    response = app.response_class(
        audio,
        mimetype="audio/ogg",
        direct_passthrough=True,
    )
    response.content_length = length
    response.headers["Accept-Ranges"] = "none"
    response.call_on_close(audio.close)
    return response

if __name__ == '__main__':
    app.run(debug=True)