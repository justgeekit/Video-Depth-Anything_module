from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from gui.api import routes
from gui.services.audio_service import AudioService
from gui.services.depth_service import DepthService
from gui.services.merge_service import MergeService
from gui.services.pipeline import Pipeline
from gui.services.video_service import VideoService

_GUI_DIR = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _GUI_DIR.parent
_UPLOAD_DIR = _PROJECT_ROOT / "uploads"
_OUTPUT_DIR = _PROJECT_ROOT / "outputs"


def create_app() -> FastAPI:
    app = FastAPI(title="Zachry Open Worlds Studio", version="1.0.0")

    # Wire up services (DI)
    video_service = VideoService()
    audio_service = AudioService()
    depth_service = DepthService()
    merge_service = MergeService()

    pipeline = Pipeline(
        video_io=video_service,
        audio_io=audio_service,
        depth_estimator=depth_service,
        merger=merge_service,
    )

    routes.configure(pipeline, _UPLOAD_DIR, _OUTPUT_DIR)
    app.include_router(routes.router)

    # Serve frontend static files
    frontend_dir = _GUI_DIR / "frontend"
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")

    return app
