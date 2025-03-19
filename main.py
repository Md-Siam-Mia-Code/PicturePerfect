import os
import secrets
import requests
import cv2
import json
import subprocess
import time
import torch
import zipfile
import threading
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from werkzeug.utils import secure_filename
from basicsr.utils import imwrite
from gfpgan import GFPGANer
from realesrgan import RealESRGANer
from basicsr.archs.rrdbnet_arch import RRDBNet
from requests.adapters import Retry, HTTPAdapter
from requests.exceptions import RequestException

app = FastAPI()
templates = Jinja2Templates(directory="static")

# Generate a random secret key
SECRET_KEY = secrets.token_hex(16)

# Create directories for input and output
UPLOAD_FOLDER = "Input"
OUTPUT_FOLDER = "Output"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Model paths
GFPGAN_MODEL_PATH = "gfpgan/weights/GFPGANv1.4.pth"
REALESRGAN_MODEL_PATH = "gfpgan/weights/RealESRGAN_x4plus.pth"
DETECTION_MODEL_PATH = "gfpgan/weights/detection_Resnet50_Final.pth"
PARSING_MODEL_PATH = "gfpgan/weights/parsing_parsenet.pth"

# Initialize GFPGAN and Real-ESRGAN
gfpganer = None
bg_upsampler = None
model_initialization_lock = threading.Lock()
model_initialized = False

version_file = "gfpgan/version.py"

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Suppress logs from external libraries except for startup logs
class StartupFilter(logging.Filter):
    def filter(self, record):
        # Allow logs that contain startup information
        if "Running on" in record.getMessage() or "Serving FastAPI app" in record.getMessage():
            return True
        # Suppress other werkzeug logs
        return False

# Apply the filter to the werkzeug logger
werkzeug_logger = logging.getLogger("werkzeug")
werkzeug_logger.setLevel(logging.INFO)
werkzeug_logger.addFilter(StartupFilter())

# Suppress other external libraries
logging.getLogger("requests").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)
logging.getLogger("torch").setLevel(logging.ERROR)
logging.getLogger("PIL").setLevel(logging.ERROR)

def format_size(bytes):
    if bytes < 1024:
        return f"{bytes} B"
    elif bytes < 1024 * 1024:
        return f"{bytes / 1024:.2f} KB"
    elif bytes < 1024 * 1024 * 1024:
        return f"{bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{bytes / (1024 * 1024 * 1024):.2f} GB"

def download_model(url, destination, model_name):
    logger.info(f"Downloading model: {model_name} from {url} to {destination}")

    session = requests.Session()
    retry_strategy = Retry(
        total=5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"],
        backoff_factor=1,  # Exponential backoff
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    # Check for an existing partial download
    downloaded_size = 0
    if os.path.exists(destination):
        downloaded_size = os.path.getsize(destination)

    headers = {}
    if downloaded_size > 0:
        headers["Range"] = f"bytes={downloaded_size}-"

    try:
        response = session.get(url, stream=True, headers=headers, timeout=10)
        response.raise_for_status()

        # Calculate total size
        if "Content-Range" in response.headers:
            total_size = int(response.headers["Content-Range"].split("/")[-1])
        else:
            total_size = downloaded_size + int(
                response.headers.get("content-length", 0)
            )

        start_time = time.time()
        last_bytes_downloaded = downloaded_size
        last_time = start_time

        # Open file in append mode if resuming; otherwise, write mode.
        mode = "ab" if downloaded_size > 0 else "wb"
        with open(destination, mode) as file:
            for data in response.iter_content(chunk_size=1024):
                file.write(data)
                downloaded_size += len(data)

                current_time = time.time()
                time_interval = current_time - last_time
                bytes_in_interval = downloaded_size - last_bytes_downloaded

                if time_interval >= 0.1:  # Update progress every 100ms
                    speed_bps = bytes_in_interval / time_interval
                    yield {
                        "status": "downloading",
                        "model_name": model_name,
                        "progress": (downloaded_size / total_size) * 100,
                        "percentage": int((downloaded_size / total_size) * 100),
                        "speed": format_size(int(speed_bps)) + "/s",
                    }
                    last_bytes_downloaded = downloaded_size
                    last_time = current_time

        yield {"status": "completed", "model_name": model_name}

    except RequestException as e:
        logger.error(
            f"Download failed for model {model_name} from {url} to {destination}. Error: {e}"
        )
        yield {"status": "error", "model_name": model_name, "error_message": str(e)}

async def initialize_models():
    global gfpganer, bg_upsampler, model_initialized
    with model_initialization_lock:
        if model_initialized:
            yield {
                "status": "info",
                "gpu_detected": (
                    torch.cuda.get_device_name(0)
                    if torch.cuda.is_available()
                    else "CPU"
                ),
                "half_precision": torch.cuda.is_available(),
            }
            yield {"status": "ready"}
            return

        model_paths = [
            (
                GFPGAN_MODEL_PATH,
                "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.4/GFPGANv1.4.pth",
                "GFPGANv1.4",
            ),
            (
                REALESRGAN_MODEL_PATH,
                "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
                "RealESRGAN_x4plus",
            ),
            (
                DETECTION_MODEL_PATH,
                "https://github.com/xinntao/facexlib/releases/download/v0.1.0/detection_Resnet50_Final.pth",
                "Face Detection",
            ),
            (
                PARSING_MODEL_PATH,
                "https://github.com/xinntao/facexlib/releases/download/v0.2.2/parsing_parsenet.pth",
                "Face Parsing",
            ),
        ]

        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            for path, url, model_name in model_paths:
                if not os.path.exists(path):
                    os.makedirs("gfpgan/weights", exist_ok=True)
                    for update in await loop.run_in_executor(executor, download_model, url, path, model_name):
                        yield update
                        if update.get("status") == "error":
                            yield {
                                "status": "model_init_error",
                                "model_name": model_name,
                                "error_message": update.get("error_message"),
                            }
                            return

        gfpganer = GFPGANer(
            model_path=GFPGAN_MODEL_PATH,
            upscale=4,
            arch="clean",
            channel_multiplier=2,
            bg_upsampler=None,
        )

        bg_model = RRDBNet(
            num_in_ch=3,
            num_out_ch=3,
            num_feat=64,
            num_block=23,
            num_grow_ch=32,
            scale=4,
        )

        half_precision = torch.cuda.is_available()
        gpu_name = torch.cuda.get_device_name(0) if half_precision else "CPU"

        bg_upsampler = RealESRGANer(
            scale=4,
            model_path=REALESRGAN_MODEL_PATH,
            model=bg_model,
            tile=400,
            tile_pad=10,  # Increase padding
            pre_pad=0,
            half=half_precision,
        )

        gfpganer.bg_upsampler = bg_upsampler
        model_initialized = True

        yield {
            "status": "info",
            "gpu_detected": gpu_name,
            "half_precision": half_precision,
        }
        yield {"status": "ready"}

@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/enhance")
async def enhance_images(request: Request, background_tasks: BackgroundTasks, upscale_factor: int = Form(4)):
    # Ensure models are initialized
    if not model_initialized:
        async for _ in initialize_models():
            pass

    gfpganer.upscale = upscale_factor
    form = await request.form()
    uploaded_files = form.getlist("files[]")
    processed_images = []

    for uploaded_file in uploaded_files:
        filename = secure_filename(uploaded_file.filename)
        input_path = os.path.join(UPLOAD_FOLDER, filename)
        output_filename = f"Enhanced_{os.path.splitext(filename)[0]}.png"
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)

        with open(input_path, "wb") as f:
            f.write(await uploaded_file.read())

        try:
            img = cv2.imread(input_path, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError(f"Corrupted file: {filename}")

            _, _, output = gfpganer.enhance(
                img, has_aligned=False, only_center_face=False, paste_back=True
            )

            imwrite(output, output_path)

            # Verify the file was written correctly
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                raise IOError(f"Failed to write file: {output_filename}")

            processed_images.append(output_filename)
        except Exception as e:
            logger.error(f"Error processing file {filename}: {e}")

    return JSONResponse({"status": "success", "images": processed_images})

@app.get("/initialize_models")
async def initialize_models_route():
    async def generate():
        try:
            async for update in initialize_models():
                yield f"data: {json.dumps(update)}\n\n"
        except Exception as e:
            logger.error(f"Error during model initialization: {e}")
            yield f"data: {json.dumps({'status': 'error', 'error_message': str(e)})}\n\n"
        finally:
            yield "event: close\ndata: close\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

@app.get("/output/{filename}")
async def output(filename: str):
    return FileResponse(os.path.join(OUTPUT_FOLDER, filename))

@app.get("/input/{filename}")
async def input_images(filename: str):
    return FileResponse(os.path.join(UPLOAD_FOLDER, filename))

@app.post("/clear_history")
async def clear_history():
    for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER]:
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
            except Exception as e:
                logger.error(f"Failed to delete {file_path}. Reason: {e}")

    return JSONResponse({"status": "success"})

@app.post("/download_all")
async def download_all():
    zip_path = os.path.join(OUTPUT_FOLDER, "Enhanced-Images.zip")
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for file_name in os.listdir(OUTPUT_FOLDER):
            file_path = os.path.join(OUTPUT_FOLDER, file_name)
            if os.path.isfile(file_path):
                try:
                    with open(file_path, "rb") as f:
                        if os.path.getsize(file_path) > 0:
                            zipf.writestr(file_name, f.read())
                        else:
                            raise IOError(f"File is empty: {file_name}")
                except Exception as e:
                    logger.error(f"Error adding file {file_name} to zip: {e}")

    return FileResponse(zip_path, filename="Enhanced-Images.zip", media_type="application/zip")

@app.post("/remove")
async def remove_file(data: dict):
    filename = data.get("remove_file")
    if filename:
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            return JSONResponse({"status": "success"})
    return JSONResponse({"status": "failure"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3015)
