"""
Dataset format converters for Road Damage Detection.
Supports converting PASCAL VOC XML to YOLO txt format and COCO json format.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from src.config import DAMAGE_CLASSES, CLASS_NAMES
from src.dataset.voc_parser import parse_voc_xml, Annotation


def voc_to_yolo_bbox(xmin: int, ymin: int, xmax: int, ymax: int, img_w: int, img_h: int) -> Tuple[float, float, float, float]:
    """Convert VOC absolute pixel coords to YOLO normalized [x_center, y_center, width, height]."""
    if img_w <= 0 or img_h <= 0:
        return 0.0, 0.0, 0.0, 0.0
    
    x_center = ((xmin + xmax) / 2.0) / img_w
    y_center = ((ymin + ymax) / 2.0) / img_h
    w = (xmax - xmin) / img_w
    h = (ymax - ymin) / img_h
    
    return min(max(x_center, 0.0), 1.0), min(max(y_center, 0.0), 1.0), min(max(w, 0.0), 1.0), min(max(h, 0.0), 1.0)


def voc_to_yolo(voc_annotations_dir: Path | str, output_dir: Path | str, class_list: Optional[List[str]] = None) -> int:
    """Convert all VOC XML files in directory to YOLO txt format."""
    voc_dir = Path(voc_annotations_dir)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if class_list is None:
        class_list = CLASS_NAMES

    class_to_idx = {c: i for i, c in enumerate(class_list)}
    converted_count = 0

    for xml_file in voc_dir.rglob("*.xml"):
        ann = parse_voc_xml(xml_file)
        if ann is None:
            continue

        yolo_lines = []
        for bbox in ann.boxes:
            if bbox.name in class_to_idx:
                cls_idx = class_to_idx[bbox.name]
                xc, yc, w, h = voc_to_yolo_bbox(
                    bbox.xmin, bbox.ymin, bbox.xmax, bbox.ymax, ann.width, ann.height
                )
                yolo_lines.append(f"{cls_idx} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}")

        out_file = out_dir / (xml_file.stem + ".txt")
        with open(out_file, "w", encoding="utf-8") as f:
            f.write("\n".join(yolo_lines) + ("\n" if yolo_lines else ""))

        converted_count += 1

    return converted_count


def voc_to_coco(voc_annotations_dir: Path | str, output_json_path: Path | str, class_list: Optional[List[str]] = None) -> Dict[str, Any]:
    """Convert VOC XML directory to single COCO format JSON."""
    voc_dir = Path(voc_annotations_dir)
    out_json = Path(output_json_path)
    out_json.parent.mkdir(parents=True, exist_ok=True)

    if class_list is None:
        class_list = CLASS_NAMES

    categories = [
        {"id": i + 1, "name": name, "supercategory": DAMAGE_CLASSES.get(name, {}).get("category", "damage")}
        for i, name in enumerate(class_list)
    ]
    name_to_cat_id = {c["name"]: c["id"] for c in categories}

    images = []
    annotations = []
    ann_id = 1
    img_id = 1

    for xml_file in voc_dir.rglob("*.xml"):
        ann = parse_voc_xml(xml_file)
        if ann is None:
            continue

        images.append({
            "id": img_id,
            "file_name": ann.filename,
            "width": ann.width,
            "height": ann.height
        })

        for bbox in ann.boxes:
            if bbox.name in name_to_cat_id:
                w = bbox.xmax - bbox.xmin
                h = bbox.ymax - bbox.ymin
                annotations.append({
                    "id": ann_id,
                    "image_id": img_id,
                    "category_id": name_to_cat_id[bbox.name],
                    "bbox": [bbox.xmin, bbox.ymin, w, h],
                    "area": w * h,
                    "iscrowd": 0
                })
                ann_id += 1

        img_id += 1

    coco_dict = {
        "images": images,
        "annotations": annotations,
        "categories": categories
    }

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(coco_dict, f, indent=2)

    return coco_dict
