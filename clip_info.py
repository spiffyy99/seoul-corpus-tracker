from __future__ import annotations

from abc import ABC, abstractmethod

class ClipInfo(ABC):
    @abstractmethod
    def get_clip_names(self) -> list[str]:
        pass

    @abstractmethod
    def get_utterances(self, clip_name: str) -> list[dict]:
        pass

    @abstractmethod
    def get_clip_sound(self, clip_name: str) -> BinaryIO:
        pass