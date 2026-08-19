"""
Visualizer module for drawing road damage bounding boxes and statistical graphs.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import numpy as np
import cv2
from PIL import Image
import matplotlib.pyplot as plt
import seaborn as sns

from src.config import DAMAGE_CLASSES
from src.dataset.voc_parser import BoundingBox, Annotation


def hex_to_bgr(hex_color: str) -> tuple:
    """Convert #RRGGBB hex color to BGR tuple for OpenCV."""
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return (b, g, r)


def draw_bounding_boxes(
    image: Union[np.ndarray, Image.Image],
    boxes: List[BoundingBox],
    show_labels: bool = True,
    show_conf: bool = True,
    line_thickness: int = 3,
    font_scale: float = 0.6
) -> np.ndarray:
    """Draw bounding boxes with damage-class specific color coding onto image.
    
    Args:
        image: RGB or BGR numpy array or PIL Image
        boxes: List of BoundingBox objects
        show_labels: Whether to render class labels
        show_conf: Whether to render confidence score if available
        line_thickness: Box outline thickness
        font_scale: Font scale multiplier
        
    Returns:
        Annotated image as RGB numpy array
    """
    if isinstance(image, Image.Image):
        img_np = np.array(image.convert("RGB"))
    else:
        img_np = image.copy()
        if len(img_np.shape) == 2:
            img_np = cv2.cvtColor(img_np, cv2.COLOR_GRAY2RGB)

    # Ensure working in RGB
    img_draw = img_np.copy()
    h, w = img_draw.shape[:2]

    for box in boxes:
        cls_info = DAMAGE_CLASSES.get(box.name, {
            "name": box.name,
            "rgb": (0, 255, 0),
            "severity": "Unknown"
        })
        color = cls_info.get("rgb", (0, 255, 0))

        # Clamp coords to image bounds
        xmin = max(0, min(box.xmin, w - 1))
        ymin = max(0, min(box.ymin, h - 1))
        xmax = max(0, min(box.xmax, w - 1))
        ymax = max(0, min(box.ymax, h - 1))

        # Draw main rectangle
        cv2.rectangle(img_draw, (xmin, ymin), (xmax, ymax), color, line_thickness)

        if show_labels:
            conf_str = f" {box.confidence * 100:.0f}%" if (show_conf and box.confidence is not None) else ""
            label_text = f"{box.name}{conf_str}"

            # Calculate label text size
            font = cv2.FONT_HERSHEY_DUPLEX
            (text_w, text_h), baseline = cv2.getTextSize(label_text, font, font_scale, 1)
            
            # Label background box
            label_ymin = max(0, ymin - text_h - baseline - 4)
            label_ymax = ymin
            label_xmax = min(w - 1, xmin + text_w + 6)
            
            cv2.rectangle(img_draw, (xmin, label_ymin), (label_xmax, label_ymax), color, -1)
            
            # Label text in contrasting white or black
            text_color = (0, 0, 0) if (color[0]*0.299 + color[1]*0.587 + color[2]*0.114) > 160 else (255, 255, 255)
            cv2.putText(
                img_draw,
                label_text,
                (xmin + 3, label_ymax - baseline - 1),
                font,
                font_scale,
                text_color,
                1,
                cv2.LINE_AA
            )

    return img_draw


def plot_damage_statistics(class_counts: Dict[str, int], title: str = "Road Damage Class Distribution") -> plt.Figure:
    """Generate a high-resolution seaborn/matplotlib bar chart of damage class counts."""
    fig, ax = plt.subplots(figsize=(9, 4.5), dpi=100)
    
    classes = list(DAMAGE_CLASSES.keys())
    counts = [class_counts.get(c, 0) for c in classes]
    colors = [DAMAGE_CLASSES[c]["color"] for c in classes]
    labels = [f"{c}\n({DAMAGE_CLASSES[c]['category']})" for c in classes]

    bars = ax.bar(labels, counts, color=colors, edgecolor="#222222", linewidth=1.2, alpha=0.9)
    
    ax.set_title(title, fontsize=14, fontweight="bold", pad=15)
    ax.set_ylabel("Damage Instances", fontsize=11, labelpad=8)
    ax.set_xlabel("Damage Category Code (JRA Standards)", fontsize=11, labelpad=8)
    ax.grid(axis="y", linestyle="--", alpha=0.3)
    ax.set_axisbelow(True)

    for bar in bars:
        height = bar.get_height()
        if height > 0:
            ax.annotate(f"{height}",
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha="center", va="bottom", fontsize=10, fontweight="bold")

    plt.tight_layout()
    return fig
