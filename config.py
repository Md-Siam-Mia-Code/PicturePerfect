# config.py
import os
import torch

# --- Project Details ---
PROJECT_VERSION = "2.0.0"

# --- Directory Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
INPUT_DIR = os.path.join(BASE_DIR, "inputs")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
GFPGAN_MODEL_DIR = os.path.join(BASE_DIR, "gfpgan", "weights")
REALESRGAN_MODEL_DIR = os.path.join(BASE_DIR, "realesrgan", "models")

# --- Model Configuration List ---
# A single source of truth for all required models.
# Structure: (model_name, filename, download_url, destination_directory)
REQUIRED_MODELS = [
    (
        "GFPGAN", "GFPGANv1.4.pth",
        "https://github.com/Md-Siam-Mia-Code/PicturePerfect/releases/download/1.0.0/GFPGANv1.4.pth",
        GFPGAN_MODEL_DIR
    ),
    (
        "RealESRGAN", "RealESRGAN_x4plus.pth",
        "https://github.com/Md-Siam-Mia-Code/PicturePerfect/releases/download/1.0.0/RealESRGAN_x4plus.pth",
        REALESRGAN_MODEL_DIR
    ),
    (
        "Face Detector", "detection_Resnet50_Final.pth",
        "https://github.com/Md-Siam-Mia-Code/PicturePerfect/releases/download/1.0.0/detection_Resnet50_Final.pth",
        GFPGAN_MODEL_DIR # This helper model belongs with GFPGAN
    ),
    (
        "Face Parser", "parsing_parsenet.pth",
        "https://github.com/Md-Siam-Mia-Code/PicturePerfect/releases/download/1.0.0/parsing_parsenet.pth",
        GFPGAN_MODEL_DIR # This helper model also belongs with GFPGAN
    )
]

# --- Model Settings ---
UPSCALE_FACTOR = 4
ARCH = 'clean'
USE_HALF_PRECISION = torch.cuda.is_available()

# --- Web Server Settings ---
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 3020

# --- Logging Configuration ---
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"