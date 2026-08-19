import os
from pathlib import Path
from typing import List

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings:
    PROJECT_NAME: str = "CrackMap Pothole & Road Damage Detection Backend"
    VERSION: str = "1.0.0"
    
    # Model
    MODEL_PATH: str = os.getenv("MODEL_PATH", str(BASE_DIR / "models" / "best.pt"))
    SAMPLES_DIR: str = os.getenv("SAMPLES_DIR", str(BASE_DIR / "samples"))
    
    # Inference defaults
    DEFAULT_CONF: float = float(os.getenv("CONF_THRESHOLD", "0.35"))
    DEFAULT_IOU: float = float(os.getenv("IOU_THRESHOLD", "0.5"))
    DEFAULT_IMGSZ: int = int(os.getenv("IMGSZ", "640"))
    
    # CORS
    ALLOWED_ORIGINS: List[str] = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000"
    ).split(",")

settings = Settings()
