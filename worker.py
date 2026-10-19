from server import app, set_clip_info
from r2_clip_info import R2ClipInfo

# Initialize with R2 for Cloudflare Worker environment
set_clip_info(R2ClipInfo(app.env.AUDIO_BUCKET))
