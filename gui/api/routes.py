import asyncio
import uuid
from pathlib import Path
from typing import Dict

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse

from gui.core.models import EncoderSize, JobConfig, ProcessingStage
from gui.services.pipeline import Pipeline

router = APIRouter()

# Injected by server.py
_pipeline: Pipeline = None  # type: ignore
_upload_dir: Path = None  # type: ignore
_output_dir: Path = None  # type: ignore

# Track active job
_current_job_id: str = ""
_processing: bool = False


def configure(pipeline: Pipeline, upload_dir: Path, output_dir: Path) -> None:
    global _pipeline, _upload_dir, _output_dir
    _pipeline = pipeline
    _upload_dir = upload_dir
    _output_dir = output_dir


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/models")
async def list_models():
    return {
        "models": [
            {"id": "vits", "name": "ViT-Small", "description": "Fastest, lower quality"},
            {"id": "vitb", "name": "ViT-Base", "description": "Balanced speed/quality"},
            {"id": "vitl", "name": "ViT-Large", "description": "Best quality, slower"},
        ]
    }


@router.post("/upload")
async def upload_video(file: UploadFile):
    if not file.filename:
        raise HTTPException(400, "No filename provided")

    ext = Path(file.filename).suffix.lower()
    if ext not in {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}:
        raise HTTPException(400, f"Unsupported video format: {ext}")

    _upload_dir.mkdir(parents=True, exist_ok=True)

    # Use original filename (overwrite if exists)
    save_path = _upload_dir / file.filename
    with open(save_path, "wb") as f:
        content = await file.read()
        f.write(content)

    return {
        "filename": file.filename,
        "path": str(save_path),
        "size_mb": round(len(content) / (1024 * 1024), 2),
    }


@router.post("/process")
async def process_video(
    filename: str,
    encoder: str = "vitl",
    input_size: int = 518,
    max_res: int = 1280,
    max_len: int = -1,
    target_fps: int = -1,
):
    global _current_job_id, _processing

    if _processing:
        raise HTTPException(409, "A job is already processing")

    input_path = _upload_dir / filename
    if not input_path.exists():
        raise HTTPException(404, f"File not found: {filename}")

    try:
        encoder_enum = EncoderSize(encoder)
    except ValueError:
        raise HTTPException(400, f"Invalid encoder: {encoder}")

    config = JobConfig(
        input_path=input_path,
        output_dir=_output_dir,
        encoder=encoder_enum,
        input_size=input_size,
        max_res=max_res,
        max_len=max_len,
        target_fps=target_fps,
    )

    _current_job_id = str(uuid.uuid4())
    _processing = True

    # Run pipeline in thread pool to avoid blocking the event loop
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, _pipeline.process, config)
    finally:
        _processing = False

    if result.success:
        return {
            "job_id": _current_job_id,
            "result": result.to_dict(),
            "downloads": {
                "src": f"/download/{config.video_stem}_src.mp4",
                "depth": f"/download/{config.video_stem}_depth.mp4",
                "rgbd": f"/download/{config.video_stem}_rgbd.mp4",
            },
        }
    else:
        raise HTTPException(500, result.error or "Processing failed")


@router.get("/progress")
async def get_progress():
    if _pipeline is None:
        return {"stage": "idle", "progress": 0, "message": ""}
    progress = _pipeline.current_progress
    return progress.to_dict()


@router.get("/download/{filename}")
async def download_file(filename: str):
    file_path = _output_dir / filename
    if not file_path.exists():
        raise HTTPException(404, f"File not found: {filename}")
    return FileResponse(
        str(file_path),
        media_type="video/mp4",
        filename=filename,
    )
