from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Tuple

import numpy as np

from .models import EncoderSize, ProgressCallback


class VideoIO(ABC):
    @abstractmethod
    def read_frames(
        self, video_path: Path, max_len: int, target_fps: int, max_res: int
    ) -> Tuple[np.ndarray, float]:
        """Read video frames, return (frames [N,H,W,3] uint8, fps)."""

    @abstractmethod
    def save_video(
        self, frames: np.ndarray, output_path: Path, fps: float, is_depths: bool = False
    ) -> None:
        """Save frames as H.264 MP4. If is_depths, normalize to 3-channel grayscale."""


class AudioIO(ABC):
    @abstractmethod
    def has_audio(self, video_path: Path) -> bool:
        """Check if video file contains an audio stream."""

    @abstractmethod
    def extract_audio(self, video_path: Path, output_path: Path) -> bool:
        """Extract audio stream to AAC file. Returns True if successful."""


class DepthEstimator(ABC):
    @abstractmethod
    def load_model(self, encoder: EncoderSize, device: str) -> None:
        """Load or switch the depth estimation model."""

    @abstractmethod
    def estimate(
        self,
        frames: np.ndarray,
        target_fps: float,
        input_size: int,
        device: str,
        fp32: bool,
        on_progress: Optional[ProgressCallback] = None,
    ) -> Tuple[np.ndarray, float]:
        """Run depth estimation, return (depths [N,H,W] float, fps)."""


class RGBDMerger(ABC):
    @abstractmethod
    def merge(
        self,
        src_path: Path,
        depth_path: Path,
        output_path: Path,
        audio_path: Optional[Path] = None,
    ) -> None:
        """Merge source + depth side-by-side, optionally muxing audio."""
