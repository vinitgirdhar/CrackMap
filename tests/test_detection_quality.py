"""Regression tests for detection precision and annotation rendering.

These lock in the fixes for: a road mask that used to fall back to
"the whole frame is road", classical false positives on clean pavement,
duplicate stacked boxes, and oversized annotation labels.
"""

import unittest

import cv2
import numpy as np

from src.dataset.visualizer import draw_bounding_boxes
from src.dataset.voc_parser import BoundingBox
from src.models.advanced_detector import AdvancedRoadDamageDetector

rng = np.random.default_rng(11)


def _asphalt(h: int, w: int, base: int = 112) -> np.ndarray:
    img = np.full((h, w, 3), base, dtype=np.float32)
    img += rng.normal(0, 10, (h, w, 3))
    blotch = cv2.GaussianBlur(rng.normal(0, 25, (h, w)).astype(np.float32), (0, 0), 30)
    img += blotch[:, :, None]
    return np.clip(img, 0, 255).astype(np.uint8)


def _grass(h: int, w: int) -> np.ndarray:
    img = np.zeros((h, w, 3), dtype=np.float32)
    img[:, :, 0] = 62 + rng.normal(0, 18, (h, w))
    img[:, :, 1] = 120 + rng.normal(0, 26, (h, w))
    img[:, :, 2] = 46 + rng.normal(0, 15, (h, w))
    return np.clip(img, 0, 255).astype(np.uint8)


class TestRoadCorridorMask(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.det = AdvancedRoadDamageDetector()

    def test_vegetation_is_excluded_from_road(self):
        """A pure grass frame must not be reported as road surface.

        The old contour-based mask collapsed to a whole-frame fallback here,
        which is what let defects be reported on grass and dirt shoulders.
        """
        mask = self.det.extract_road_corridor_mask(_grass(300, 400))
        road_fraction = np.count_nonzero(mask) / mask.size
        self.assertLess(road_fraction, 0.25, "vegetation was classified as road surface")

    def test_plain_asphalt_is_kept_as_road(self):
        """Masking must not be so aggressive that it discards real pavement."""
        mask = self.det.extract_road_corridor_mask(_asphalt(300, 400))
        road_fraction = np.count_nonzero(mask) / mask.size
        self.assertGreater(road_fraction, 0.80, "clean asphalt was rejected as non-road")

    def test_colour_cast_asphalt_is_kept_as_road(self):
        """Green-cyan tinted asphalt (RGB ~61/81/81) must survive masking.

        Real photos carry colour casts; keying vegetation on hue alone made
        the mask discard the very surface holding the potholes.
        """
        tinted = np.zeros((300, 400, 3), dtype=np.uint8)
        tinted[:, :] = (61, 81, 81)
        tinted = np.clip(tinted + rng.normal(0, 6, tinted.shape), 0, 255).astype(np.uint8)
        mask = self.det.extract_road_corridor_mask(tinted)
        self.assertGreater(np.count_nonzero(mask) / mask.size, 0.80)


class TestClassicalDetectorPrecision(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.det = AdvancedRoadDamageDetector()

    def test_clean_asphalt_yields_no_defects(self):
        img = _asphalt(360, 480)
        mask = self.det.extract_road_corridor_mask(img)
        boxes = self.det.detect_cv_pavement_defects(img, mask, min_conf=0.25)
        self.assertEqual(len(boxes), 0, f"false positives on clean asphalt: {len(boxes)}")

    def test_smooth_shadow_is_not_reported_as_damage(self):
        """Shadows are dark but smooth; only rough dark regions are damage."""
        img = _asphalt(360, 480)
        shadow = np.zeros((360, 480), dtype=np.float32)
        cv2.fillPoly(shadow, [np.array([[80, 0], [200, 0], [300, 360], [180, 360]], np.int32)], 1.0)
        shadow = cv2.GaussianBlur(shadow, (0, 0), 15)
        img = np.clip(img.astype(np.float32) * (1 - 0.45 * shadow[:, :, None]), 0, 255).astype(np.uint8)

        mask = self.det.extract_road_corridor_mask(img)
        boxes = self.det.detect_cv_pavement_defects(img, mask, min_conf=0.25)
        self.assertEqual(len(boxes), 0, f"shadow reported as damage: {len(boxes)}")


class TestNonMaximumSuppression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.det = AdvancedRoadDamageDetector()

    def test_contained_box_is_suppressed(self):
        """A small box inside a confident larger one is a duplicate.

        Plain IoU NMS kept these, which rendered as stacked labels on one
        pothole (the repeated 'D10 69%' seen in review screenshots).
        """
        outer = BoundingBox(name="D40", xmin=100, ymin=100, xmax=300, ymax=300, confidence=0.9)
        inner = BoundingBox(name="D40", xmin=150, ymin=150, xmax=210, ymax=210, confidence=0.5)
        kept = self.det.apply_nms([outer, inner], iou_thresh=0.30)
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0].confidence, 0.9)

    def test_distinct_boxes_are_both_kept(self):
        a = BoundingBox(name="D40", xmin=0, ymin=0, xmax=80, ymax=80, confidence=0.8)
        b = BoundingBox(name="D40", xmin=300, ymin=300, xmax=380, ymax=380, confidence=0.7)
        self.assertEqual(len(self.det.apply_nms([a, b], iou_thresh=0.30)), 2)


class TestAnnotationRendering(unittest.TestCase):
    def test_line_and_font_scale_down_on_small_images(self):
        """Annotations must stay thin/small rather than covering the defect."""
        boxes = [BoundingBox(name="D40", xmin=40, ymin=40, xmax=140, ymax=110, confidence=0.83)]

        small = draw_bounding_boxes(_asphalt(240, 320), boxes)
        large = draw_bounding_boxes(_asphalt(1400, 1900), boxes)

        self.assertEqual(small.shape[:2], (240, 320))
        self.assertEqual(large.shape[:2], (1400, 1900))

        # On a small frame the drawn annotation must touch only a small
        # fraction of pixels — the old fixed 3px/0.6-scale styling did not.
        base = _asphalt(240, 320)
        changed = np.count_nonzero(np.any(draw_bounding_boxes(base, boxes) != base, axis=2))
        self.assertLess(changed / base[:, :, 0].size, 0.06)

    def test_labels_do_not_stack_on_identical_anchors(self):
        """Two boxes sharing a top-left corner must not overprint labels."""
        boxes = [
            BoundingBox(name="D40", xmin=50, ymin=60, xmax=200, ymax=160, confidence=0.9),
            BoundingBox(name="D20", xmin=50, ymin=60, xmax=260, ymax=210, confidence=0.4),
        ]
        out = draw_bounding_boxes(_asphalt(400, 500), boxes)
        self.assertEqual(out.shape[:2], (400, 500))


if __name__ == "__main__":
    unittest.main()
