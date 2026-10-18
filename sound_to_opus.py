
from pathlib import Path
import av
from av.audio.resampler import AudioResampler

INPUT_DIR = Path("sound")
OUTPUT_DIR = Path("sound_opus")
BITRATE = 32_000

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

files = sorted(INPUT_DIR.rglob("*.flac"))
success = 0
failed = 0

for src in files:
    dst = (OUTPUT_DIR / src.relative_to(INPUT_DIR)).with_suffix(".opus")
    dst.parent.mkdir(parents=True, exist_ok=True)

    try:
        with av.open(str(src)) as inp:
            audio = inp.streams.audio[0]

            with av.open(str(dst), mode="w", format="opus") as out:
                stream = out.add_stream("libopus", rate=48000)
                stream.bit_rate = BITRATE
                stream.layout = "mono"

                resampler = AudioResampler(
                    format="fltp",
                    layout="mono",
                    rate=48000,
                )

                for frame in inp.decode(audio):
                    for resampled_frame in resampler.resample(frame):
                        for packet in stream.encode(resampled_frame):
                            out.mux(packet)

                # Flush the resampler.
                for resampled_frame in resampler.resample(None):
                    for packet in stream.encode(resampled_frame):
                        out.mux(packet)

                # Flush the encoder.
                for packet in stream.encode(None):
                    out.mux(packet)

        success += 1
        print(f"Converted: {src}")

    except Exception as e:
        failed += 1
        print(f"FAILED: {src}: {e}")

print(f"\nFinished. Converted: {success}, Failed: {failed}")
