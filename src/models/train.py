"""
PyTorch Training Module for Road Damage Detection.
Supports training and fine-tuning on PASCAL VOC formatted RDD datasets.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import time
import torch
from torch.utils.data import Dataset, DataLoader
from PIL import Image
import numpy as np

from src.config import CLASS_NAMES, CLASS_NAME_TO_ID, MODELS_DIR
from src.dataset.voc_parser import parse_voc_xml, Annotation
from src.models.detector import RoadDamageDetectorNet, build_road_damage_detector


class RoadDamageVOCDataset(Dataset):
    """PyTorch Dataset for PASCAL VOC formatted Road Damage annotations."""

    def __init__(self, dataset_dir: Path | str, transform=None):
        self.dataset_dir = Path(dataset_dir)
        self.transform = transform
        self.annotations: List[Annotation] = []

        xml_files = sorted(list(self.dataset_dir.rglob("*.xml")))
        for xml_file in xml_files:
            ann = parse_voc_xml(xml_file)
            if ann is not None and ann.has_damage:
                # Resolve image file
                img_path = self.dataset_dir / "JPEGImages" / ann.filename
                if not img_path.exists():
                    img_path = xml_file.parent.parent / "JPEGImages" / ann.filename
                if not img_path.exists():
                    img_path = xml_file.parent.parent / "images" / ann.filename
                
                if img_path.exists():
                    ann.filepath = img_path
                    self.annotations.append(ann)

    def __len__(self) -> int:
        return len(self.annotations)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
        ann = self.annotations[idx]
        img = Image.open(ann.filepath).convert("RGB")
        img_np = np.array(img).transpose((2, 0, 1))
        img_tensor = torch.from_numpy(img_np).float() / 255.0

        boxes = []
        labels = []

        for b in ann.boxes:
            if b.name in CLASS_NAME_TO_ID:
                boxes.append([b.xmin, b.ymin, b.xmax, b.ymax])
                labels.append(CLASS_NAME_TO_ID[b.name])

        if not boxes:
            boxes = torch.zeros((0, 4), dtype=torch.float32)
            labels = torch.zeros((0,), dtype=torch.int64)
        else:
            boxes = torch.as_tensor(boxes, dtype=torch.float32)
            labels = torch.as_tensor(labels, dtype=torch.int64)

        target = {
            "boxes": boxes,
            "labels": labels,
            "image_id": torch.tensor([idx])
        }

        return img_tensor, target


def collate_fn(batch):
    return tuple(zip(*batch))


def train_road_damage_model(
    dataset_dir: Path | str,
    architecture: str = "fasterrcnn_mobilenet",
    num_epochs: int = 5,
    batch_size: int = 4,
    learning_rate: float = 0.005,
    output_checkpoint_name: str = "road_damage_detector.pth",
    device: Optional[str] = None,
    progress_callback: Optional[callable] = None
) -> Dict[str, Any]:
    """Train or fine-tune RoadDamageDetector model.
    
    Args:
        dataset_dir: Root of VOC dataset with Annotations/ and JPEGImages/
        architecture: Model backbone ('fasterrcnn_mobilenet' or 'ssdlite_mobilenet')
        num_epochs: Number of training epochs
        batch_size: Batch size
        learning_rate: Initial learning rate
        output_checkpoint_name: Filename to save weights
        device: 'cuda' or 'cpu'
        progress_callback: Optional fn(epoch, epoch_loss, total_epochs)
        
    Returns:
        Dictionary with training history and saved model path
    """
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    dataset = RoadDamageVOCDataset(dataset_dir)
    if len(dataset) == 0:
        raise ValueError(f"No annotated damage images found in {dataset_dir}")

    dataloader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=True,
        collate_fn=collate_fn
    )

    model = build_road_damage_detector(architecture=architecture, device=device)
    model.train()

    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.SGD(params, lr=learning_rate, momentum=0.9, weight_decay=0.0005)
    lr_scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=3, gamma=0.1)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = MODELS_DIR / output_checkpoint_name

    history = {"epochs": [], "loss": [], "elapsed_time_sec": []}
    start_total = time.time()

    print(f"Starting training on {len(dataset)} samples for {num_epochs} epochs on {device}...")

    for epoch in range(1, num_epochs + 1):
        epoch_loss = 0.0
        model.train()
        start_epoch = time.time()

        for images, targets in dataloader:
            images = [img.to(device) for img in images]
            targets = [{k: v.to(device) for k, v in t.items()} for t in targets]

            loss_dict = model(images, targets)
            losses = sum(loss for loss in loss_dict.values())

            optimizer.zero_grad()
            losses.backward()
            optimizer.step()

            epoch_loss += losses.item()

        lr_scheduler.step()
        avg_loss = epoch_loss / max(1, len(dataloader))
        epoch_time = time.time() - start_epoch

        history["epochs"].append(epoch)
        history["loss"].append(round(avg_loss, 4))
        history["elapsed_time_sec"].append(round(epoch_time, 2))

        print(f"Epoch [{epoch}/{num_epochs}] - Loss: {avg_loss:.4f} ({epoch_time:.2f}s)")

        if progress_callback:
            progress_callback(epoch, avg_loss, num_epochs)

    # Save checkpoint
    torch.save({
        "epoch": num_epochs,
        "model_state_dict": model.state_dict(),
        "architecture": architecture,
        "class_names": CLASS_NAMES,
    }, str(out_path))

    print(f"Model saved to {out_path} (Total time: {time.time() - start_total:.2f}s)")

    return {
        "checkpoint_path": str(out_path),
        "history": history,
        "num_samples": len(dataset),
    }
