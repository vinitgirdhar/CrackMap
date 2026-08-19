"""
Dataset downloader and synthetic/sample generator for testing and offline evaluation.
"""

import urllib.request
import zipfile
import tarfile
from pathlib import Path
from typing import Dict, Optional, List, Any
import numpy as np
import cv2
import xml.etree.ElementTree as ET

from src.config import DATA_DIR, SAMPLES_DIR, DAMAGE_CLASSES, OFFICIAL_DATASET_URLS


def download_dataset(
    dataset_key: str,
    output_dir: Path | str = DATA_DIR,
    progress_callback: Optional[callable] = None
) -> Optional[Path]:
    """Download and extract an official RDD dataset from the IEEE BigData Cup S3 archive.
    
    Args:
        dataset_key: One of key in OFFICIAL_DATASET_URLS (e.g. 'RDD2020_InJaCz')
        output_dir: Target destination directory
        progress_callback: Optional callback fn(downloaded_bytes, total_bytes)
        
    Returns:
        Path to extracted directory or None
    """
    if dataset_key not in OFFICIAL_DATASET_URLS:
        raise ValueError(f"Unknown dataset '{dataset_key}'. Available: {list(OFFICIAL_DATASET_URLS.keys())}")

    url = OFFICIAL_DATASET_URLS[dataset_key]
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    filename = url.split("/")[-1]
    archive_path = out_dir / filename
    extract_target = out_dir / dataset_key

    # Download if not present
    if not archive_path.exists():
        print(f"Downloading {dataset_key} from {url}...")
        
        def reporthook(count, block_size, total_size):
            if progress_callback:
                progress_callback(count * block_size, total_size)

        urllib.request.urlretrieve(url, archive_path, reporthook=reporthook)
        print(f"Saved archive to {archive_path}")

    # Extract
    print(f"Extracting {archive_path} to {extract_target}...")
    extract_target.mkdir(parents=True, exist_ok=True)
    if filename.endswith(".zip"):
        with zipfile.ZipFile(archive_path, "r") as z:
            z.extractall(extract_target)
    elif filename.endswith(".tar.gz") or filename.endswith(".tgz"):
        with tarfile.open(archive_path, "r:gz") as t:
            t.extractall(extract_target)

    print("Extraction complete!")
    return extract_target


def create_synthetic_road_image(
    width: int = 640,
    height: int = 480,
    damage_types: Optional[List[str]] = None,
    seed: Optional[int] = None
) -> tuple[np.ndarray, List[Dict[str, Any]]]:
    """Generate a realistic synthetic asphalt road image with damage artifacts for testing.
    
    Args:
        width: Image width
        height: Image height
        damage_types: List of damage classes to embed (e.g., ['D00', 'D40'])
        seed: Random seed for reproducibility
        
    Returns:
        (image_rgb, annotations_list)
    """
    if seed is not None:
        np.random.seed(seed)

    # Base asphalt texture with noise and lighting gradient
    base_color = np.random.randint(60, 95)
    asphalt = np.full((height, width, 3), base_color, dtype=np.uint8)

    # Add realistic asphalt grain / granular noise
    grain = np.random.normal(0, 15, (height, width, 3)).astype(np.int16)
    asphalt = np.clip(asphalt.astype(np.int16) + grain, 20, 240).astype(np.uint8)

    # Add perspective roadway lighting gradient (darker near camera / road surface perspective)
    y_grad = np.linspace(0.85, 1.15, height)[:, np.newaxis, np.newaxis]
    asphalt = np.clip(asphalt.astype(np.float32) * y_grad, 0, 255).astype(np.uint8)

    # Draw lane marking (white or yellow)
    lane_x = int(width * 0.15)
    cv2.line(asphalt, (lane_x, int(height * 0.2)), (int(lane_x * 0.6), height), (220, 220, 220), 10)
    
    right_lane_x = int(width * 0.85)
    cv2.line(asphalt, (right_lane_x, int(height * 0.2)), (int(width * 0.95), height), (220, 220, 220), 10)

    if damage_types is None:
        all_types = list(DAMAGE_CLASSES.keys())
        damage_types = [np.random.choice(all_types)]

    boxes = []

    for dtype in damage_types:
        if dtype == "D00":  # Longitudinal crack along wheel path
            cx = int(width * np.random.uniform(0.3, 0.7))
            ymin = int(height * np.random.uniform(0.2, 0.4))
            ymax = int(height * np.random.uniform(0.7, 0.9))
            
            # Draw zigzag jagged crack
            pts = []
            cur_x = cx
            for y in range(ymin, ymax, 15):
                cur_x += np.random.randint(-6, 7)
                pts.append((cur_x, y))
            
            pts = np.array(pts, dtype=np.int32)
            cv2.polylines(asphalt, [pts], isClosed=False, color=(25, 25, 25), thickness=3)
            # Crack shadow / edge highlight
            cv2.polylines(asphalt, [pts + [1, 0]], isClosed=False, color=(90, 90, 90), thickness=1)

            xmin = max(0, int(np.min(pts[:, 0]) - 15))
            xmax = min(width - 1, int(np.max(pts[:, 0]) + 15))
            boxes.append({"name": dtype, "xmin": xmin, "ymin": ymin, "xmax": xmax, "ymax": ymax})

        elif dtype == "D10":  # Transverse crack across road
            cy = int(height * np.random.uniform(0.4, 0.75))
            xmin = int(width * np.random.uniform(0.2, 0.35))
            xmax = int(width * np.random.uniform(0.65, 0.85))
            
            pts = []
            cur_y = cy
            for x in range(xmin, xmax, 15):
                cur_y += np.random.randint(-4, 5)
                pts.append((x, cur_y))
            
            pts = np.array(pts, dtype=np.int32)
            cv2.polylines(asphalt, [pts], isClosed=False, color=(20, 20, 20), thickness=3)
            
            ymin = max(0, int(np.min(pts[:, 1]) - 15))
            ymax = min(height - 1, int(np.max(pts[:, 1]) + 15))
            boxes.append({"name": dtype, "xmin": xmin, "ymin": ymin, "xmax": xmax, "ymax": ymax})

        elif dtype == "D20":  # Alligator / fatigue mesh crack
            cx = int(width * np.random.uniform(0.35, 0.65))
            cy = int(height * np.random.uniform(0.45, 0.75))
            rw = np.random.randint(60, 110)
            rh = np.random.randint(40, 80)
            
            xmin = max(0, cx - rw)
            xmax = min(width - 1, cx + rw)
            ymin = max(0, cy - rh)
            ymax = min(height - 1, cy + rh)

            # Draw network grid of fine cracks
            for _ in range(8):
                p1 = (np.random.randint(xmin, xmax), np.random.randint(ymin, ymax))
                p2 = (np.random.randint(xmin, xmax), np.random.randint(ymin, ymax))
                cv2.line(asphalt, p1, p2, (30, 30, 30), 2)
            
            boxes.append({"name": dtype, "xmin": xmin, "ymin": ymin, "xmax": xmax, "ymax": ymax})

        elif dtype == "D40":  # Pothole
            cx = int(width * np.random.uniform(0.35, 0.65))
            cy = int(height * np.random.uniform(0.5, 0.8))
            ax_w = np.random.randint(40, 75)
            ax_h = np.random.randint(25, 45)

            # Dark cavity with inner rough texture
            cv2.ellipse(asphalt, (cx, cy), (ax_w, ax_h), np.random.randint(-15, 15), 0, 360, (20, 20, 20), -1)
            cv2.ellipse(asphalt, (cx - 2, cy - 2), (int(ax_w * 0.7), int(ax_h * 0.7)), 0, 0, 360, (10, 10, 10), -1)
            # Outer broken rim
            cv2.ellipse(asphalt, (cx, cy), (ax_w + 3, ax_h + 3), 0, 0, 360, (110, 110, 110), 2)

            xmin = max(0, cx - ax_w - 5)
            xmax = min(width - 1, cx + ax_w + 5)
            ymin = max(0, cy - ax_h - 5)
            ymax = min(height - 1, cy + ax_h + 5)
            boxes.append({"name": dtype, "xmin": xmin, "ymin": ymin, "xmax": xmax, "ymax": ymax})

        elif dtype in ["D43", "D44"]:  # Blur / degraded line
            lx = int(width * 0.5)
            cv2.line(asphalt, (lx, int(height * 0.3)), (lx, height), (160, 160, 160), 8)
            # Add smudge noise over line
            smudge = np.random.randint(0, 255, (height, width), dtype=np.uint8)
            smudge = cv2.GaussianBlur(smudge, (21, 21), 0)
            mask = (smudge > 140)
            asphalt[mask] = np.clip(asphalt[mask] * 0.8, 0, 255).astype(np.uint8)

            boxes.append({"name": dtype, "xmin": lx - 30, "ymin": int(height * 0.35), "xmax": lx + 30, "ymax": int(height * 0.85)})

    return asphalt, boxes


def save_voc_xml(image_filename: str, width: int, height: int, boxes: List[Dict[str, Any]], xml_path: Path):
    """Save bounding boxes to a PASCAL VOC formatted XML file."""
    root = ET.Element("annotation")
    
    folder = ET.SubElement(root, "folder")
    folder.text = "JPEGImages"
    
    filename = ET.SubElement(root, "filename")
    filename.text = image_filename
    
    size = ET.SubElement(root, "size")
    ET.SubElement(size, "width").text = str(width)
    ET.SubElement(size, "height").text = str(height)
    ET.SubElement(size, "depth").text = "3"
    
    for box in boxes:
        obj = ET.SubElement(root, "object")
        ET.SubElement(obj, "name").text = box["name"]
        ET.SubElement(obj, "pose").text = "Unspecified"
        ET.SubElement(obj, "truncated").text = "0"
        ET.SubElement(obj, "difficult").text = "0"
        
        bndbox = ET.SubElement(obj, "bndbox")
        ET.SubElement(bndbox, "xmin").text = str(box["xmin"])
        ET.SubElement(bndbox, "ymin").text = str(box["ymin"])
        ET.SubElement(bndbox, "xmax").text = str(box["xmax"])
        ET.SubElement(bndbox, "ymax").text = str(box["ymax"])
        
    tree = ET.ElementTree(root)
    tree.write(xml_path, encoding="utf-8", xml_declaration=True)


def create_sample_dataset(target_dir: Path | str = SAMPLES_DIR, num_samples: int = 12) -> Path:
    """Generate a sample dataset structure with JPEGImages and Annotations for immediate testing."""
    target_path = Path(target_dir)
    img_dir = target_path / "JPEGImages"
    ann_dir = target_path / "Annotations"
    img_dir.mkdir(parents=True, exist_ok=True)
    ann_dir.mkdir(parents=True, exist_ok=True)

    damage_keys = list(DAMAGE_CLASSES.keys())
    
    for i in range(num_samples):
        # Pick 1-2 damage classes per image
        sample_types = [damage_keys[i % len(damage_keys)]]
        if i % 3 == 0:
            sample_types.append(damage_keys[(i + 2) % len(damage_keys)])

        img_filename = f"sample_{i+1:03d}.jpg"
        xml_filename = f"sample_{i+1:03d}.xml"

        img, boxes = create_synthetic_road_image(
            width=640,
            height=480,
            damage_types=sample_types,
            seed=42 + i
        )

        cv2.imwrite(str(img_dir / img_filename), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
        save_voc_xml(img_filename, 640, 480, boxes, ann_dir / xml_filename)

    print(f"Created {num_samples} sample images & VOC XML annotations in {target_path}")
    return target_path
