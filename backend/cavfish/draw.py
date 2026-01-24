# backend/cavfish/draw.py
from __future__ import annotations

from typing import Dict, Any, List
import cv2
import numpy as np


def draw_overlay(image_bgr: np.ndarray, prediction: Dict[str, Any]) -> np.ndarray:
    img = image_bgr.copy()

    # Draw keypoints
    for kp in prediction["keypoints"]:
        x, y = int(round(kp["x"])), int(round(kp["y"]))
        cv2.circle(img, (x, y), 3, (0, 255, 255), -1)  # yellow

    # Draw phenotype lines
    kp_xy = np.array([[kp["x"], kp["y"]] for kp in prediction["keypoints"]], dtype=np.float32)
    for ph in prediction.get("phenotypes", []):
        i, j = ph["pair"]
        p1 = tuple(np.round(kp_xy[i]).astype(int))
        p2 = tuple(np.round(kp_xy[j]).astype(int))
        cv2.line(img, p1, p2, (255, 255, 0), 2)  # cyan

    return img

