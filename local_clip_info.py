from __future__ import annotations
from clip_info import ClipInfo
from pathlib import Path

class LocalClipInfo(ClipInfo):
    def __init__(self):
        self.audio_dir = Path('sound_opus')

    def get_clip_sound(self, clip_name: str) -> tuple[bytes, int]:
        audio_path = self.audio_dir / f"{clip_name}.opus"
        data = audio_path.read_bytes()
        return data, len(data)