import json
import subprocess
from pathlib import Path

from gui.core.interfaces import AudioIO
from gui.services.ffmpeg_util import find_ffmpeg, find_ffprobe


class AudioService(AudioIO):
    def has_audio(self, video_path: Path) -> bool:
        try:
            result = subprocess.run(
                [
                    find_ffprobe(),
                    "-v", "quiet",
                    "-print_format", "json",
                    "-show_streams",
                    "-select_streams", "a",
                    str(video_path),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            data = json.loads(result.stdout)
            return len(data.get("streams", [])) > 0
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            return False

    def extract_audio(self, video_path: Path, output_path: Path) -> bool:
        try:
            result = subprocess.run(
                [
                    find_ffmpeg(),
                    "-y",
                    "-i", str(video_path),
                    "-vn",
                    "-acodec", "aac",
                    "-b:a", "192k",
                    str(output_path),
                ],
                capture_output=True,
                text=True,
                timeout=300,
            )
            return result.returncode == 0 and output_path.exists()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
