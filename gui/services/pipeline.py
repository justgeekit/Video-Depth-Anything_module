import traceback
from typing import Optional

import torch

from gui.core.interfaces import AudioIO, DepthEstimator, RGBDMerger, VideoIO
from gui.core.models import (
    JobConfig,
    JobProgress,
    ProcessingResult,
    ProcessingStage,
    ProgressCallback,
)


class Pipeline:
    def __init__(
        self,
        video_io: VideoIO,
        audio_io: AudioIO,
        depth_estimator: DepthEstimator,
        merger: RGBDMerger,
    ):
        self._video = video_io
        self._audio = audio_io
        self._depth = depth_estimator
        self._merger = merger
        self._progress = JobProgress()
        self._device = "cuda" if torch.cuda.is_available() else "cpu"

    @property
    def current_progress(self) -> JobProgress:
        return self._progress

    def _report(self, stage: ProcessingStage, progress: float, message: str) -> None:
        self._progress.stage = stage
        self._progress.progress = progress
        self._progress.message = message

    def _on_depth_progress(self, stage: str, pct: float, message: str) -> None:
        self._report(ProcessingStage.ESTIMATING_DEPTH, pct, message)

    def process(self, config: JobConfig) -> ProcessingResult:
        try:
            config.output_dir.mkdir(parents=True, exist_ok=True)

            # 1. Extract audio from ORIGINAL input (before any preprocessing)
            self._report(ProcessingStage.EXTRACTING_AUDIO, 0.0, "Checking for audio...")
            has_audio = self._audio.has_audio(config.input_path)
            audio_extracted = False
            if has_audio:
                self._report(ProcessingStage.EXTRACTING_AUDIO, 0.5, "Extracting audio...")
                audio_extracted = self._audio.extract_audio(
                    config.input_path, config.audio_path
                )

            # 2. Read video frames
            self._report(ProcessingStage.READING_FRAMES, 0.0, "Reading video frames...")
            frames, fps = self._video.read_frames(
                config.input_path, config.max_len, config.target_fps, config.max_res
            )
            self._report(
                ProcessingStage.READING_FRAMES,
                1.0,
                f"Read {frames.shape[0]} frames at {fps:.1f} fps",
            )

            # 3. Load depth model
            self._report(
                ProcessingStage.ESTIMATING_DEPTH, 0.0, "Loading depth model..."
            )
            self._depth.load_model(config.encoder, self._device)

            # 4. Estimate depth
            depths, fps = self._depth.estimate(
                frames,
                fps,
                input_size=config.input_size,
                device=self._device,
                fp32=config.fp32,
                on_progress=self._on_depth_progress,
            )

            # 5. Save source video
            self._report(ProcessingStage.SAVING_SOURCE, 0.0, "Saving source video...")
            self._video.save_video(frames, config.src_path, fps)
            self._report(ProcessingStage.SAVING_SOURCE, 1.0, "Source video saved")

            # 6. Save depth video (3-channel grayscale)
            self._report(ProcessingStage.SAVING_DEPTH, 0.0, "Saving depth video...")
            self._video.save_video(depths, config.depth_path, fps, is_depths=True)
            self._report(ProcessingStage.SAVING_DEPTH, 1.0, "Depth video saved")

            # 7. Merge RGBD
            self._report(ProcessingStage.MERGING_RGBD, 0.0, "Merging RGBD video...")
            audio_for_merge = config.audio_path if audio_extracted else None
            self._merger.merge(
                config.src_path, config.depth_path, config.rgbd_path, audio_for_merge
            )
            self._report(ProcessingStage.MERGING_RGBD, 1.0, "RGBD merge complete")

            self._report(ProcessingStage.COMPLETE, 1.0, "Processing complete!")

            return ProcessingResult(
                success=True,
                src_path=config.src_path,
                depth_path=config.depth_path,
                rgbd_path=config.rgbd_path,
                has_audio=audio_extracted,
            )

        except Exception as e:
            self._report(ProcessingStage.FAILED, 0.0, str(e))
            traceback.print_exc()
            return ProcessingResult(success=False, error=str(e))
