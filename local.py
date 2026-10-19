from server import app, set_clip_info
from local_clip_info import LocalClipInfo
from flask import send_from_directory
import os
from pathlib import Path

DIST_DIR = Path(__file__).parent / 'dist'

# Serve frontend for local development
@app.get("/")
def index():
    return send_from_directory(str(DIST_DIR), 'index.html')

@app.get("/<path:path>")
def static_files(path):
    return send_from_directory(str(DIST_DIR), path)


if __name__ == '__main__':
    set_clip_info(LocalClipInfo())
    # Change to project directory to ensure relative paths work
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    app.run(debug=True, port=3000)
  




