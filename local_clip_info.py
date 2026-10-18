from __future__ import annotations
from clip_info import ClipInfo
from pathlib import Path
import json

class LocalClipInfo(ClipInfo):
    def __init__(self):
        self.clip_dir = Path('transcripts_json')
        self.audio_dir = Path('sound_opus')

    def get_clip_names(self) -> list[str]:
        return [
            clip.stem
            for clip in self.clip_dir.iterdir()
            if clip.is_file() and clip.suffix == ".json"
        ]

    def get_utterances(self, clip_name: str) -> list[dict]:
        target_clip = self.clip_dir / f"{clip_name}.json"

        with open(target_clip, "r", encoding="utf-8") as target_file:
            content = json.load(target_file)

        return content["tiers"][3]["entries"]


    def get_clip_sound(self, clip_name: str) -> BinaryIO:
        audio_path = self.audio_dir / f"{clip_name}.opus"

        if not audio_path.is_file():
            raise FileNotFoundError(clip_name)

        return audio_path.open("rb")