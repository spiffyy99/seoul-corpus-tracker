from __future__ import annotations

from io import BytesIO
from typing import BinaryIO

from pyodide.ffi import run_sync

from clip_info import ClipInfo


class R2ClipInfo(ClipInfo):
    def __init__(self, r2_bucket):
        self.r2_bucket = r2_bucket

    async def _get_clip_sound_async(
        self, clip_name: str
    ) -> tuple[BinaryIO, int]:
        key = f"sound_opus/{clip_name}.opus"
        obj = await self.r2_bucket.get(key)

        if obj is None:
            raise FileNotFoundError(f"Audio clip not found: {key}")

        body = await obj.arrayBuffer()
        data = bytes(body)
        return BytesIO(data), len(data)

    def get_clip_sound(self, clip_name: str) -> tuple[BinaryIO, int]:
        return run_sync(self._get_clip_sound_async(clip_name))