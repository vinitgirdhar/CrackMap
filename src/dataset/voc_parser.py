"""
PASCAL VOC XML Parser for Road Damage Detection Datasets.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
import xml.etree.ElementTree as ET
from collections import Counter

from src.config import DAMAGE_CLASSES


@dataclass
class BoundingBox:
    name: str
    xmin: int
    ymin: int
    xmax: int
    ymax: int
    confidence: Optional[float] = 1.0

    @property
    def width(self) -> int:
        return max(0, self.xmax - self.xmin)

    @property
    def height(self) -> int:
        return max(0, self.ymax - self.ymin)

    @property
    def area(self) -> int:
        return self.width * self.height

    @property
    def is_valid(self) -> bool:
        return self.xmax > self.xmin and self.ymax > self.ymin


@dataclass
class Annotation:
    filename: str
    width: int
    height: int
    depth: int = 3
    boxes: List[BoundingBox] = field(default_factory=list)
    filepath: Optional[Path] = None

    @property
    def num_objects(self) -> int:
        return len(self.boxes)

    @property
    def has_damage(self) -> bool:
        return len(self.boxes) > 0


def parse_voc_xml(xml_path: Path | str) -> Optional[Annotation]:
    """Parse a single PASCAL VOC XML annotation file.
    
    Args:
        xml_path: Path to the .xml file
        
    Returns:
        Annotation object or None if parsing failed
    """
    xml_path = Path(xml_path)
    if not xml_path.exists():
        return None

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        filename = root.findtext("filename") or xml_path.stem + ".jpg"
        
        size_node = root.find("size")
        if size_node is not None:
            width = int(size_node.findtext("width", "0"))
            height = int(size_node.findtext("height", "0"))
            depth = int(size_node.findtext("depth", "3"))
        else:
            width, height, depth = 0, 0, 3

        boxes = []
        for obj in root.findall("object"):
            name = obj.findtext("name", "").strip()
            bndbox = obj.find("bndbox")
            if bndbox is not None and name:
                try:
                    xmin = int(float(bndbox.findtext("xmin", "0")))
                    ymin = int(float(bndbox.findtext("ymin", "0")))
                    xmax = int(float(bndbox.findtext("xmax", "0")))
                    ymax = int(float(bndbox.findtext("ymax", "0")))
                    
                    bbox = BoundingBox(name=name, xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax)
                    if bbox.is_valid:
                        boxes.append(bbox)
                except (ValueError, TypeError):
                    continue

        return Annotation(
            filename=filename,
            width=width,
            height=height,
            depth=depth,
            boxes=boxes,
            filepath=xml_path
        )
    except Exception as e:
        print(f"Error parsing {xml_path}: {e}")
        return None


def parse_voc_dataset_dir(dataset_dir: Path | str) -> Dict[str, Any]:
    """Parse an entire dataset directory in PASCAL VOC format.
    
    Supports structure:
    dataset_dir/
      Annotations/
      JPEGImages/
      ImageSets/Main/ (optional)
      
    or nested municipality folders (e.g., Japan/Adachi/Annotations/)
    """
    dataset_dir = Path(dataset_dir)
    annotations: List[Annotation] = []
    class_counter: Counter = Counter()

    xml_files = list(dataset_dir.rglob("*.xml"))
    for xml_file in xml_files:
        ann = parse_voc_xml(xml_file)
        if ann is not None:
            annotations.append(ann)
            for b in ann.boxes:
                class_counter[b.name] += 1

    total_images = len(annotations)
    damaged_images = sum(1 for a in annotations if a.has_damage)

    return {
        "total_images": total_images,
        "damaged_images": damaged_images,
        "undamaged_images": total_images - damaged_images,
        "total_boxes": sum(class_counter.values()),
        "class_distribution": dict(class_counter),
        "annotations": annotations,
    }
