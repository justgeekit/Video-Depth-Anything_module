from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Optional


class EncoderSize(str, Enum):
    SMALL = "vits"
    BASE = "vitb"
    LARGE = "vitl"


class ProcessingStage(str, Enum):
    UPLOADING = "uploading"
    READING_FRAMES = "reading_frames"
    EXTRACTING_AUDIO = "extracting_audio"
    ESTIMATING_DEPTH = "estimating_depth"
    SAVING_SOURCE = "saving_source"
    SAVING_DEPTH = "saving_depth"
    MERGING_RGBD = "merging_rgbd"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class JobConfig:
    input_path: Path
    output_dir: Path
    encoder: EncoderSize = EncoderSize.LARGE
    input_size: int = 518
    max_res: int = 1280
    max_len: int = -1
    target_fps: int = -1
    fp32: bool = False

    @property
    def video_stem(self) -> str:
        return self.input_path.stem

    @property
    def src_path(self) -> Path:
        return self.output_dir / f"{self.video_stem}_src.mp4"

    @property
    def depth_path(self) -> Path:
        return self.output_dir / f"{self.video_stem}_depth.mp4"

    @property
    def audio_path(self) -> Path:
        return self.output_dir / f"{self.video_stem}_audio.aac"

    @property
    def rgbd_path(self) -> Path:
        return self.output_dir / f"{self.video_stem}_rgbd.mp4"


ProgressCallback = Callable[[str, float, str], None]


@dataclass
class JobProgress:
    stage: ProcessingStage = ProcessingStage.UPLOADING
    progress: float = 0.0
    message: str = ""

    def to_dict(self) -> dict:
        return {
            "stage": self.stage.value,
            "progress": self.progress,
            "message": self.message,
        }


@dataclass
class ProcessingResult:
    success: bool
    src_path: Optional[Path] = None
    depth_path: Optional[Path] = None
    rgbd_path: Optional[Path] = None
    has_audio: bool = False
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "src_path": str(self.src_path) if self.src_path else None,
            "depth_path": str(self.depth_path) if self.depth_path else None,
            "rgbd_path": str(self.rgbd_path) if self.rgbd_path else None,
            "has_audio": self.has_audio,
            "error": self.error,
        }
