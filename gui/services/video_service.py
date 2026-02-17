import sys
from pathlib import Path
from typing import Tuple

import imageio
import numpy as np

from gui.core.interfaces import VideoIO

# Add project root to path so upstream imports work
_PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from utils.dc_utils import read_video_frames as _read_frames


class VideoService(VideoIO):
    def read_frames(
        self, video_path: Path, max_len: int, target_fps: int, max_res: int
    ) -> Tuple[np.ndarray, float]:
        frames, fps = _read_frames(str(video_path), max_len, target_fps, max_res)
        return frames, fps

    def save_video(
        self, frames: np.ndarray, output_path: Path, fps: float, is_depths: bool = False
    ) -> None:
        writer = imageio.get_writer(
            str(output_path),
            fps=fps,
            macro_block_size=1,
            codec="libx264",
            ffmpeg_params=["-crf", "18"],
        )
        try:
            if is_depths:
                self._write_depth_frames(writer, frames)
            else:
                for i in range(frames.shape[0]):
                    writer.append_data(frames[i])
        finally:
            writer.close()

    def _write_depth_frames(self, writer, depths: np.ndarray) -> None:
        """Normalize depths to 3-channel grayscale uint8 for ffmpeg hstack compatibility."""
        d_min, d_max = depths.min(), depths.max()
        for i in range(depths.shape[0]):
            depth = depths[i]
            depth_norm = ((depth - d_min) / (d_max - d_min) * 255).astype(np.uint8)
            # Stack to 3-channel grayscale so hstack works with RGB source
            depth_3ch = np.stack([depth_norm] * 3, axis=-1)
            writer.append_data(depth_3ch)
