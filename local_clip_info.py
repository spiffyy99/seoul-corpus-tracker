from __future__ import annotations
from clip_info import ClipInfo
from pathlib import Path
from typing import BinaryIO

class LocalClipInfo(ClipInfo):
    def __init__(self):
        self.audio_dir = Path('sound_opus')

    def get_clip_sound(self, clip_name: str) -> tuple[BinaryIO, int]:
        audio_path = self.audio_dir / f"{clip_name}.opus"
        return audio_path.open("rb"), audio_path.stat().st_size