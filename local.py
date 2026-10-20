from server import app, set_clip_info
from local_clip_info import LocalClipInfo
import os

if __name__ == '__main__':
    set_clip_info(LocalClipInfo())
    # Change to project directory to ensure relative paths work
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    app.run(debug=True, port=3000)
  




