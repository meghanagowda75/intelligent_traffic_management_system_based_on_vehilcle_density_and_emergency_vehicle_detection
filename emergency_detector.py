import cv2
import numpy as np

def is_emergency_vehicle(frame, bbox):
    x1, y1, x2, y2 = bbox
    crop = frame[y1:y2, x1:x2]
    if crop.size == 0:
        return False
    h = crop.shape[0]
    roof = crop[0:max(5, int(0.3*h)), :]
    hsv = cv2.cvtColor(roof, cv2.COLOR_BGR2HSV)

    lower_red1 = np.array([0,120,150]); upper_red1 = np.array([10,255,255])
    lower_red2 = np.array([160,120,150]); upper_red2 = np.array([180,255,255])
    mask_r1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask_r2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask_red = cv2.bitwise_or(mask_r1, mask_r2)

    lower_blue = np.array([90,80,80]); upper_blue = np.array([140,255,255])
    mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)

    red_prop = np.sum(mask_red>0) / (roof.shape[0]*roof.shape[1])
    blue_prop = np.sum(mask_blue>0) / (roof.shape[0]*roof.shape[1])

    return red_prop > 0.005 or blue_prop > 0.005
