from server import app, set_clip_info
from r2_clip_info import R2ClipInfo
from workers import wsgi, env

# Initialize with R2 for Cloudflare Worker environment
set_clip_info(R2ClipInfo(env.AUDIO_BUCKET))

Default = wsgi.entrypoint(app)