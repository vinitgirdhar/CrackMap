"""
Configuration and constants for Road Damage Detector (CrackMap).
Based on the Japan Road Association (JRA) standards and IEEE BigData Cup RDD benchmarks.
"""

from pathlib import Path

# Base Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SAMPLES_DIR = PROJECT_ROOT / "samples"
MODELS_DIR = PROJECT_ROOT / "models_saved"

# 8 Core JRA Classes with descriptions and severity levels
DAMAGE_CLASSES = {
    "D00": {
        "id": 1,
        "name": "Longitudinal Crack (Wheel Mark)",
        "category": "Linear Crack",
        "description": "Linear crack along wheel tracks caused by repetitive vehicle loads.",
        "severity": "Medium",
        "severity_score": 3,
        "color": "#FF4B4B",       # Red-Orange
        "rgb": (255, 75, 75),
    },
    "D01": {
        "id": 2,
        "name": "Longitudinal Crack (Joint)",
        "category": "Linear Crack",
        "description": "Linear crack at construction joints and asphalt seams.",
        "severity": "Low",
        "severity_score": 2,
        "color": "#FFA500",       # Orange
        "rgb": (255, 165, 0),
    },
    "D10": {
        "id": 3,
        "name": "Transverse Crack (Equal Interval)",
        "category": "Linear Crack",
        "description": "Lateral crack across the road caused by thermal shrinkage / weather cycles.",
        "severity": "Medium",
        "severity_score": 3,
        "color": "#FFD700",       # Gold / Yellow
        "rgb": (255, 215, 0),
    },
    "D11": {
        "id": 4,
        "name": "Transverse Crack (Joint)",
        "category": "Linear Crack",
        "description": "Lateral crack located specifically at construction seams.",
        "severity": "Low",
        "severity_score": 2,
        "color": "#ADFF2F",       # Green-Yellow
        "rgb": (173, 255, 47),
    },
    "D20": {
        "id": 5,
        "name": "Alligator / Fatigue Crack",
        "category": "Alligator Crack",
        "description": "Interconnected fatigue network cracking; indicates structural subgrade failure.",
        "severity": "High",
        "severity_score": 5,
        "color": "#FF007F",       # Deep Rose / Magenta
        "rgb": (255, 0, 127),
    },
    "D40": {
        "id": 6,
        "name": "Pothole / Rutting / Bump",
        "category": "Surface Hazard",
        "description": "Pavement depression, surface separation, or hazardous cavity.",
        "severity": "Critical",
        "severity_score": 5,
        "color": "#E60000",       # Crimson Red
        "rgb": (230, 0, 0),
    },
    "D43": {
        "id": 7,
        "name": "Crosswalk Marking Blur",
        "category": "Marking Degradation",
        "description": "Faded or obscured pedestrian zebra crossing markings.",
        "severity": "Low",
        "severity_score": 1,
        "color": "#00BFFF",       # Deep Sky Blue
        "rgb": (0, 191, 255),
    },
    "D44": {
        "id": 8,
        "name": "Lane Line Marking Blur",
        "category": "Marking Degradation",
        "description": "Faded lane boundaries, center lines, or road demarcation lines.",
        "severity": "Low",
        "severity_score": 1,
        "color": "#1E90FF",       # Dodger Blue
        "rgb": (30, 144, 255),
    },
}

# 4 Unified International Competition Classes (RDD2020 / RDD2022 / ORDDC)
UNIFIED_CLASSES = ["D00", "D10", "D20", "D40"]

CLASS_NAMES = list(DAMAGE_CLASSES.keys())
CLASS_ID_TO_NAME = {v["id"]: k for k, v in DAMAGE_CLASSES.items()}
CLASS_NAME_TO_ID = {k: v["id"] for k, v in DAMAGE_CLASSES.items()}

# S3 and FigShare official download URLs from README
OFFICIAL_DATASET_URLS = {
    "RDD2020_InJaCz": "https://mycityreport.s3-ap-northeast-1.amazonaws.com/02_RoadDamageDataset/public_data/IEEE_bigdata_RDD2020/train.tar.gz",
    "RDD2022_Japan": "https://bigdatacup.s3.ap-northeast-1.amazonaws.com/2022/CRDDC2022/RDD2022/Country_Specific_Data_CRDDC2022/RDD2022_Japan.zip",
    "RDD2022_India": "https://bigdatacup.s3.ap-northeast-1.amazonaws.com/2022/CRDDC2022/RDD2022/Country_Specific_Data_CRDDC2022/RDD2022_India.zip",
    "RDD2022_Czech": "https://bigdatacup.s3.ap-northeast-1.amazonaws.com/2022/CRDDC2022/RDD2022/Country_Specific_Data_CRDDC2022/RDD2022_Czech.zip",
    "RDD2022_United_States": "https://bigdatacup.s3.ap-northeast-1.amazonaws.com/2022/CRDDC2022/RDD2022/Country_Specific_Data_CRDDC2022/RDD2022_United_States.zip",
}
