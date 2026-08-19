"""
Unit and Integration Test Suite for Modernized CrackMap Suite.
"""

import unittest
import sys
from pathlib import Path
import numpy as np
from PIL import Image

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import DAMAGE_CLASSES, CLASS_NAMES
from src.dataset import (
    parse_voc_xml,
    parse_voc_dataset_dir,
    voc_to_yolo,
    voc_to_coco,
    create_sample_dataset,
    draw_bounding_boxes,
    BoundingBox
)
from src.models import (
    build_road_damage_detector,
    RoadDamageInferenceEngine,
    compute_iou,
    calculate_map
)
from src.ui_components import generate_simulated_gps_damage_data, build_pydeck_map


class TestCrackMapPipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_dir = Path("./test_samples")
        create_sample_dataset(cls.test_dir, num_samples=4)

    def test_01_damage_classes_config(self):
        """Verify 8 JRA classes are correctly configured."""
        self.assertEqual(len(DAMAGE_CLASSES), 8)
        self.assertIn("D00", DAMAGE_CLASSES)
        self.assertIn("D40", DAMAGE_CLASSES)
        self.assertEqual(len(CLASS_NAMES), 8)

    def test_02_voc_parser(self):
        """Verify VOC XML parsing."""
        xml_files = list(self.test_dir.glob("Annotations/*.xml"))
        self.assertGreater(len(xml_files), 0)
        
        ann = parse_voc_xml(xml_files[0])
        self.assertIsNotNone(ann)
        self.assertGreater(ann.width, 0)
        self.assertGreater(ann.height, 0)
        self.assertTrue(ann.has_damage)

    def test_03_dataset_dir_summary(self):
        """Verify directory level dataset summary parsing."""
        summary = parse_voc_dataset_dir(self.test_dir)
        self.assertEqual(summary["total_images"], 4)
        self.assertGreater(summary["total_boxes"], 0)

    def test_04_converters(self):
        """Verify VOC to YOLO and COCO conversion."""
        yolo_out = self.test_dir / "yolo"
        count = voc_to_yolo(self.test_dir / "Annotations", yolo_out)
        self.assertEqual(count, 4)
        
        coco_out = self.test_dir / "coco.json"
        coco_res = voc_to_coco(self.test_dir / "Annotations", coco_out)
        self.assertEqual(len(coco_res["images"]), 4)
        self.assertGreater(len(coco_res["annotations"]), 0)

    def test_05_visualizer(self):
        """Verify bounding box rendering."""
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        boxes = [BoundingBox(name="D00", xmin=10, ymin=10, xmax=100, ymax=100, confidence=0.9)]
        annotated = draw_bounding_boxes(img, boxes)
        self.assertEqual(annotated.shape, (480, 640, 3))

    def test_06_model_instantiation_and_inference(self):
        """Verify PyTorch model builds and runs inference on image tensor."""
        engine = RoadDamageInferenceEngine(architecture="fasterrcnn_mobilenet", device="cpu")
        sample_img = self.test_dir / "JPEGImages" / "sample_001.jpg"
        result = engine.predict(sample_img)
        self.assertIsNotNone(result)
        self.assertGreater(result.inference_time_ms, 0)

    def test_07_evaluation_metrics(self):
        """Verify IoU and mAP computation."""
        iou = compute_iou([0, 0, 10, 10], [0, 0, 10, 10])
        self.assertAlmostEqual(iou, 1.0)

        iou_none = compute_iou([0, 0, 5, 5], [10, 10, 20, 20])
        self.assertAlmostEqual(iou_none, 0.0)

        gts = {"img1": [BoundingBox(name="D00", xmin=0, ymin=0, xmax=10, ymax=10)]}
        preds = {"img1": [BoundingBox(name="D00", xmin=0, ymin=0, xmax=10, ymax=10, confidence=0.95)]}
        map_res = calculate_map(gts, preds)
        self.assertAlmostEqual(map_res["mAP_50"], 1.0)

    def test_08_gps_gis_components(self):
        """Verify GPS dataset and PyDeck deck building."""
        df_gps = generate_simulated_gps_damage_data(num_points=10)
        self.assertEqual(len(df_gps), 10)
        deck = build_pydeck_map(df_gps, view_mode="Both")
        self.assertIsNotNone(deck)


if __name__ == "__main__":
    unittest.main()
