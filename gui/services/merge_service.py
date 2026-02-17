import subprocess
from pathlib import Path
from typing import Optional

from gui.core.interfaces import RGBDMerger
from gui.services.ffmpeg_util import find_ffmpeg


class MergeService(RGBDMerger):
    def merge(
        self,
        src_path: Path,
        depth_path: Path,
        output_path: Path,
        audio_path: Optional[Path] = None,
    ) -> None:
        cmd = [
            find_ffmpeg(), "-y",
            "-i", str(src_path),
            "-i", str(depth_path),
        ]

        if audio_path and audio_path.exists():
            cmd += ["-i", str(audio_path)]
            cmd += [
                "-filter_complex", "[0:v][1:v]hstack=inputs=2[v]",
                "-map", "[v]",
                "-map", "2:a",
                "-c:v", "libx264",
                "-crf", "18",
                "-c:a", "aac",
                "-shortest",
                str(output_path),
            ]
        else:
            cmd += [
                "-filter_complex", "[0:v][1:v]hstack=inputs=2[v]",
                "-map", "[v]",
                "-c:v", "libx264",
                "-crf", "18",
                "-an",
                str(output_path),
            ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg merge failed: {result.stderr}")
