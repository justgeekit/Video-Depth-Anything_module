"""Locate a full-build ffmpeg/ffprobe that supports libx264."""

import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

# Known paths for full-build ffmpeg on Windows (WinGet installs)
_WINGET_FFMPEG_DIRS = list(
    Path.home().glob(
        "AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg*/ffmpeg-*-full_build/bin"
    )
)


@lru_cache(maxsize=1)
def find_ffmpeg() -> str:
    """Return path to ffmpeg with libx264 support."""
    # Check WinGet full-build first
    for d in _WINGET_FFMPEG_DIRS:
        candidate = d / "ffmpeg.exe"
        if candidate.exists():
            return str(candidate)

    # Check WinGet Links directory
    links_candidate = Path.home() / "AppData/Local/Microsoft/WinGet/Links/ffmpeg.exe"
    if links_candidate.exists():
        # Verify it has libx264
        try:
            result = subprocess.run(
                [str(links_candidate), "-encoders"],
                capture_output=True, text=True, timeout=10,
            )
            if "libx264" in result.stdout:
                return str(links_candidate)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    # Fall back to PATH (might be a limited build)
    path_ffmpeg = shutil.which("ffmpeg")
    if path_ffmpeg:
        return path_ffmpeg

    raise FileNotFoundError("ffmpeg not found")


@lru_cache(maxsize=1)
def find_ffprobe() -> str:
    """Return path to ffprobe."""
    # Check WinGet full-build first
    for d in _WINGET_FFMPEG_DIRS:
        candidate = d / "ffprobe.exe"
        if candidate.exists():
            return str(candidate)

    # Check WinGet Links
    links_candidate = Path.home() / "AppData/Local/Microsoft/WinGet/Links/ffprobe.exe"
    if links_candidate.exists():
        return str(links_candidate)

    path_ffprobe = shutil.which("ffprobe")
    if path_ffprobe:
        return path_ffprobe

    raise FileNotFoundError("ffprobe not found")
