"""
Command Line Interface (CLI) runner for CrackMap & RoadDamageDetector.
Usage:
    python run_cli.py detect --image path/to/road.jpg
    python run_cli.py dataset --create-samples --sample-count 10
    python run_cli.py convert --voc-dir samples/Annotations --to yolo --output yolo_labels
    python run_cli.py train --epochs 3 --batch-size 4
    python run_cli.py evaluate --dataset samples
    python run_cli.py app
"""

import argparse
import sys
from pathlib import Path
import subprocess

from src.config import DAMAGE_CLASSES, SAMPLES_DIR, DATA_DIR
from src.dataset import (
    create_sample_dataset,
    parse_voc_dataset_dir,
    voc_to_yolo,
    voc_to_coco,
    download_dataset
)
from src.models import (
    RoadDamageInferenceEngine,
    AdvancedRoadDamageDetector,
    train_road_damage_model,
    evaluate_detector
)


def main():
    parser = argparse.ArgumentParser(description="CrackMap - AI Road Damage Detector CLI Suite")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # App Command
    subparsers.add_parser("app", help="Launch interactive Streamlit Web UI")

    # Detect Command
    detect_p = subparsers.add_parser("detect", help="Run AI road damage detection on an image")
    detect_p.add_argument("--image", type=str, required=True, help="Path to input image")
    detect_p.add_argument("--engine", choices=["ensemble", "yolo", "cv", "pytorch"], default="ensemble", help="AI Detection Engine")
    detect_p.add_argument("--conf", type=float, default=0.25, help="Confidence threshold")
    detect_p.add_argument("--output", type=str, default="annotated_output.jpg", help="Path to save output")

    # Dataset Command
    ds_p = subparsers.add_parser("dataset", help="Manage or generate datasets")
    ds_p.add_argument("--create-samples", action="store_true", help="Generate synthetic sample dataset")
    ds_p.add_argument("--sample-count", type=int, default=12, help="Number of samples to generate")
    ds_p.add_argument("--download", type=str, default=None, help="Dataset key to download (e.g., RDD2020_InJaCz)")
    ds_p.add_argument("--inspect", type=str, default=None, help="Directory of dataset to inspect")

    # Convert Command
    conv_p = subparsers.add_parser("convert", help="Convert VOC annotations")
    conv_p.add_argument("--voc-dir", type=str, required=True, help="Path to VOC Annotations/ directory")
    conv_p.add_argument("--to", choices=["yolo", "coco"], required=True, help="Target format")
    conv_p.add_argument("--output", type=str, required=True, help="Output file/directory")

    # Train Command
    train_p = subparsers.add_parser("train", help="Train PyTorch detector")
    train_p.add_argument("--dataset", type=str, default=str(SAMPLES_DIR), help="Dataset root directory")
    train_p.add_argument("--epochs", type=int, default=3, help="Number of epochs")
    train_p.add_argument("--batch-size", type=int, default=4, help="Batch size")
    train_p.add_argument("--lr", type=float, default=0.005, help="Learning rate")
    train_p.add_argument("--arch", type=str, default="fasterrcnn_mobilenet", help="Architecture")

    # Evaluate Command
    eval_p = subparsers.add_parser("evaluate", help="Evaluate model benchmark performance (mAP)")
    eval_p.add_argument("--dataset", type=str, default=str(SAMPLES_DIR), help="Dataset directory")
    eval_p.add_argument("--conf", type=float, default=0.25, help="Confidence threshold")

    args = parser.parse_args()

    if args.command == "app" or len(sys.argv) == 1:
        print("Launching Streamlit App...")
        subprocess.run(["streamlit", "run", "app.py"])

    elif args.command == "detect":
        img_path = Path(args.image)
        if not img_path.exists():
            print(f"Error: File {img_path} not found.")
            return

        print(f"Running detection on {img_path} with {args.engine} engine...")
        if args.engine == "pytorch":
            engine = RoadDamageInferenceEngine(confidence_threshold=args.conf)
            res = engine.predict(img_path)
        else:
            detector = AdvancedRoadDamageDetector(confidence_threshold=args.conf)
            mode_str = "Ensemble" if args.engine == "ensemble" else ("YOLO" if args.engine == "yolo" else "Computer Vision")
            res = detector.predict(img_path, custom_conf_threshold=args.conf, engine_mode=mode_str)
        
        import cv2
        cv2.imwrite(args.output, cv2.cvtColor(res.image, cv2.COLOR_RGB2BGR))
        print(f"Detection complete in {res.inference_time_ms:.1f}ms!")
        print(f"Found {res.num_detections} damage instances. Severity Score: {res.severity_score}")
        for i, b in enumerate(res.boxes):
            print(f"  [{i+1}] {b.name} ({DAMAGE_CLASSES.get(b.name, {}).get('name')}) - Conf: {b.confidence*100:.1f}% - Box: [{b.xmin}, {b.ymin}, {b.xmax}, {b.ymax}]")
        print(f"Saved annotated image to {args.output}")

    elif args.command == "dataset":
        if args.download:
            download_dataset(args.download)
        elif args.create_samples:
            create_sample_dataset(SAMPLES_DIR, num_samples=args.sample_count)
        elif args.inspect:
            stats = parse_voc_dataset_dir(args.inspect)
            print("Dataset Summary:")
            print(f"  Total Images: {stats['total_images']}")
            print(f"  Damaged Images: {stats['damaged_images']}")
            print(f"  Total Damage Boxes: {stats['total_boxes']}")
            print(f"  Class Breakdown: {stats['class_distribution']}")

    elif args.command == "convert":
        if args.to == "yolo":
            count = voc_to_yolo(args.voc_dir, args.output)
            print(f"Converted {count} XML files to YOLO format in {args.output}")
        elif args.to == "coco":
            res = voc_to_coco(args.voc_dir, args.output)
            print(f"Converted {len(res['images'])} images with {len(res['annotations'])} objects to COCO in {args.output}")

    elif args.command == "train":
        print(f"Training on dataset {args.dataset}...")
        train_road_damage_model(
            dataset_dir=args.dataset,
            architecture=args.arch,
            num_epochs=args.epochs,
            batch_size=args.batch_size,
            learning_rate=args.lr
        )

    elif args.command == "evaluate":
        print(f"Evaluating on {args.dataset}...")
        engine = RoadDamageInferenceEngine(confidence_threshold=args.conf)
        res = evaluate_detector(args.dataset, engine, confidence_threshold=args.conf)
        print(f"Evaluation Results:")
        print(f"  mAP@0.5: {res['mAP_50']*100:.2f}%")
        for cls_name, metrics in res["class_metrics"].items():
            print(f"  - {cls_name}: Precision={metrics['precision']*100:.1f}%, Recall={metrics['recall']*100:.1f}%, F1={metrics['f1']*100:.1f}%, AP={metrics['ap']*100:.1f}% (N={metrics['support']})")


if __name__ == "__main__":
    main()
