from __future__ import annotations
from flask import Flask, request

app = Flask(__name__)
clip_info = None


def set_clip_info(clip_info_impl):
    global clip_info
    clip_info = clip_info_impl


@app.get("/api/clips/<clip_name>/play")
def play_sound(clip_name: str):
    # Generate ETag from clip name (for R2, you'd use the object's ETag)
    etag = f'"{clip_name}"'

    # Check If-None-Match for conditional request
    if_none_match = request.headers.get('If-None-Match')
    if if_none_match and if_none_match == etag:
        return '', 304

    audio, length = clip_info.get_clip_sound(clip_name)
    response = app.response_class(
        audio,
        mimetype="audio/ogg",
        direct_passthrough=True,
    )
    response.content_length = length
    response.headers["Accept-Ranges"] = "none"
    response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    response.headers["ETag"] = etag
    response.call_on_close(audio.close)
    return response

