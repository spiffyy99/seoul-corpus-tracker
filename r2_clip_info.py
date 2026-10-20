from __future__ import annotations
from clip_info import ClipInfo
from typing import BinaryIO
from io import BytesIO


class R2ClipInfo(ClipInfo):
    """
    R2-based clip info implementation for Cloudflare Workers.

    The r2_bucket parameter is the R2 bucket binding from the Worker environment.
    """

    def __init__(self, r2_bucket):
        self.r2_bucket = r2_bucket

    async def get_clip_sound(self, clip_name: str) -> tuple[BinaryIO, int]:
        key = f"{clip_name}.opus"
        object = await self.r2_bucket.get(key)

        if object is None:
            raise FileNotFoundError(f"Audio clip not found: {key}")

        # Read into BytesIO for Flask compatibility
        body = await object.body.read()
        return BytesIO(body), len(body)
