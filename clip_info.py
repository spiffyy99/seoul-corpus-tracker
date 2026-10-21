from __future__ import annotations
from abc import ABC, abstractmethod
import re

def parse_clip_name(clip_name: str) -> dict:
    match = re.fullmatch(r"(s\d{2})([mf])(\d{2})([mf])([1-6])", clip_name)
    if not match:
        raise ValueError(f"Invalid clip name: {clip_name}")
    speaker_id, speaker_gender, speaker_age, interviewer_gender, segment = match.groups()
    return {
        "speaker_id": speaker_id,
        "speaker_gender": "male" if speaker_gender == "m" else "female",
        "speaker_age": int(speaker_age),
        "interviewer_gender": "male" if interviewer_gender == "m" else "female",
        "segment_number": int(segment),
    }

class ClipInfo(ABC):
    @abstractmethod
    def get_clip_sound(self, clip_name: str) -> tuple[bytes, int]:
        pass
