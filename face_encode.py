import os
import sys
import urllib.request
import numpy as np
import cv2

ROOT = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(ROOT, "models")
OUT_DIR = os.path.join(ROOT, "out")
YUNET = os.path.join(MODELS_DIR, "face_detection_yunet_2023mar.onnx")
SFACE = os.path.join(MODELS_DIR, "face_recognition_sface_2021dec.onnx")
YUNET_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
SFACE_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx"
FR_COSINE = getattr(cv2.FaceRecognizerSF, "FR_COSINE", 0)

def ensure_models():
    os.makedirs(MODELS_DIR, exist_ok=True)
    for path, url in [(YUNET, YUNET_URL), (SFACE, SFACE_URL)]:
        if not os.path.exists(path) or os.path.getsize(path) < 10000:
            print("Downloading", os.path.basename(path))
            req = urllib.request.Request(url, headers={"User-Agent": "task3-demo"})
            with urllib.request.urlopen(req) as r, open(path, "wb") as f:
                f.write(r.read())
    return YUNET, SFACE

def build():
    yunet, sface = ensure_models()
    detector = cv2.FaceDetectorYN.create(yunet, "", (320, 320), 0.9, 0.3, 5000)
    recognizer = cv2.FaceRecognizerSF.create(sface, "")
    return detector, recognizer

def detect_faces(detector, img):
    h, w = img.shape[:2]
    detector.setInputSize((w, h))
    _, faces = detector.detect(img)
    return [] if faces is None else list(faces)

def largest_face(faces):
    return max(faces, key=lambda f: float(f[2]) * float(f[3]))

def encode(recognizer, img, face):
    aligned = recognizer.alignCrop(img, face)
    feat = recognizer.feature(aligned)
    return feat, aligned

def similarity(recognizer, a, b):
    return float(recognizer.match(a, b, FR_COSINE))

def encode_path(path):
    img = cv2.imread(path)
    if img is None:
        raise SystemExit("Could not read image: " + path)
    detector, recognizer = build()
    faces = detect_faces(detector, img)
    if not faces:
        raise SystemExit("No face detected in " + path)
    face = largest_face(faces)
    feat, aligned = encode(recognizer, img, face)
    os.makedirs(OUT_DIR, exist_ok=True)
    crop_path = os.path.join(OUT_DIR, "face.png")
    embed_path = os.path.join(OUT_DIR, "embedding.npy")
    cv2.imwrite(crop_path, aligned)
    np.save(embed_path, feat)
    return {
        "faces": len(faces),
        "box": [int(face[0]), int(face[1]), int(face[2]), int(face[3])],
        "score": float(face[-1]),
        "embedding": feat,
        "crop": crop_path,
        "embed_file": embed_path,
    }

