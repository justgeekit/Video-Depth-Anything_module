import sys
import unittest.mock
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import torch

from gui.core.interfaces import DepthEstimator
from gui.core.models import EncoderSize, ProgressCallback

_PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from video_depth_anything.video_depth import VideoDepthAnything

MODEL_CONFIGS = {
    "vits": {"encoder": "vits", "features": 64, "out_channels": [48, 96, 192, 384]},
    "vitb": {"encoder": "vitb", "features": 128, "out_channels": [96, 192, 384, 768]},
    "vitl": {"encoder": "vitl", "features": 256, "out_channels": [256, 512, 1024, 1024]},
}

CHECKPOINT_DIR = Path(_PROJECT_ROOT) / "checkpoints"


class DepthService(DepthEstimator):
    def __init__(self):
        self._model: Optional[VideoDepthAnything] = None
        self._current_encoder: Optional[EncoderSize] = None
        self._device: str = "cpu"

    def load_model(self, encoder: EncoderSize, device: str) -> None:
        if self._model is not None and self._current_encoder == encoder:
            return  # Already loaded

        config = MODEL_CONFIGS[encoder.value]
        model = VideoDepthAnything(**config)
        ckpt_path = CHECKPOINT_DIR / f"video_depth_anything_{encoder.value}.pth"
        model.load_state_dict(
            torch.load(str(ckpt_path), map_location="cpu"), strict=True
        )
        model = model.to(device).eval()

        self._model = model
        self._current_encoder = encoder
        self._device = device

    def estimate(
        self,
        frames: np.ndarray,
        target_fps: float,
        input_size: int,
        device: str,
        fp32: bool,
        on_progress: Optional[ProgressCallback] = None,
    ) -> Tuple[np.ndarray, float]:
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        if on_progress:
            return self._estimate_with_progress(
                frames, target_fps, input_size, device, fp32, on_progress
            )

        depths, fps = self._model.infer_video_depth(
            frames, target_fps, input_size=input_size, device=device, fp32=fp32
        )
        return depths, fps

    def _estimate_with_progress(
        self,
        frames: np.ndarray,
        target_fps: float,
        input_size: int,
        device: str,
        fp32: bool,
        on_progress: ProgressCallback,
    ) -> Tuple[np.ndarray, float]:
        """Run inference with tqdm monkey-patching for progress callbacks."""
        import tqdm as tqdm_module

        original_tqdm = tqdm_module.tqdm

        class ProgressTqdm:
            """Drop-in tqdm replacement that forwards progress to our callback."""

            def __init__(self, iterable=None, *args, **kwargs):
                self._iterable = iterable
                self._total = kwargs.get("total", None)
                if self._total is None and iterable is not None:
                    try:
                        self._total = len(iterable)
                    except TypeError:
                        self._total = None
                self._n = 0

            def __iter__(self):
                for item in self._iterable:
                    yield item
                    self._n += 1
                    if self._total and self._total > 0:
                        pct = self._n / self._total
                        on_progress(
                            "estimating_depth",
                            pct,
                            f"Processing window {self._n}/{self._total}",
                        )

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def update(self, n=1):
                self._n += n

        # Monkey-patch tqdm in the video_depth module
        import video_depth_anything.video_depth as vd_module

        original_vd_tqdm = vd_module.tqdm
        vd_module.tqdm = ProgressTqdm

        try:
            depths, fps = self._model.infer_video_depth(
                frames, target_fps, input_size=input_size, device=device, fp32=fp32
            )
        finally:
            vd_module.tqdm = original_vd_tqdm

        return depths, fps
