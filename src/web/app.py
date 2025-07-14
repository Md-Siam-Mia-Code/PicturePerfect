import os
import cv2
import json
import zipfile
import logging
from typing import List
from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from werkzeug.utils import secure_filename
from basicsr.utils import imwrite

import config
from src.core.enhancer import PicturePerfectEnhancer

app = FastAPI(title="PicturePerfect API", version=config.PROJECT_VERSION)
app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")

templates = Jinja2Templates(directory=config.STATIC_DIR)
enhancer = PicturePerfectEnhancer(config)
logger = logging.getLogger(__name__)

# --- NEW API ENDPOINTS FOR MODEL MANAGEMENT ---

@app.get("/api/status")
async def get_status():
    """Checks for missing models and returns system info."""
    missing_models = enhancer.check_models()
    system_info = enhancer.get_system_info()
    return JSONResponse({
        "missing_models": missing_models,
        "system_info": system_info
    })

@app.post("/api/download_model")
async def download_model_route(model_info: dict):
    """Streams the download progress for a single requested model."""
    async def stream_download():
        try:
            for update in enhancer.download_model(model_info):
                yield f"data: {json.dumps(update)}\n\n"
        except Exception as e:
            logger.error(f"Download stream failed: {e}", exc_info=True)
            yield f"data: {json.dumps({'status': 'error', 'model_name': model_info.get('name', 'Unknown'), 'error_message': str(e)})}\n\n"
    return StreamingResponse(stream_download(), media_type="text/event-stream")

@app.post("/api/load_models")
async def load_models_route():
    """Triggers the loading of models into GPU/CPU memory."""
    try:
        enhancer.load_models_into_memory()
        return JSONResponse({"status": "success", "message": "Models loaded into memory."})
    except Exception as e:
        logger.error(f"Failed to load models into memory: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to load models: {str(e)}")
        
# --- END OF NEW API ENDPOINTS ---

@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/enhance")
async def enhance_images(files: List[UploadFile] = File(...)):
    if not enhancer.is_initialized:
        raise HTTPException(status_code=400, detail="Models are not yet loaded and ready.")
    
    processed_images = []
    for uploaded_file in files:
        filename = secure_filename(uploaded_file.filename)
        input_path = os.path.join(config.INPUT_DIR, filename)
        try:
            with open(input_path, "wb") as f: f.write(await uploaded_file.read())
            img = cv2.imread(input_path, cv2.IMREAD_COLOR)
            if img is None: continue
            restored_img = enhancer.enhance(img, upscale_factor=config.UPSCALE_FACTOR)
            if restored_img is None: continue
            output_filename = f"Enhanced_{os.path.splitext(filename)[0]}.png"
            output_path = os.path.join(config.OUTPUT_DIR, output_filename)
            imwrite(restored_img, output_path)
            processed_images.append(output_filename)
        except Exception as e:
            logger.error(f"Error processing file {filename}: {e}", exc_info=True)
            
    return JSONResponse({"status": "success", "images": processed_images})

@app.get("/output/{filename}")
async def get_output_image(filename: str):
    file_path = os.path.join(config.OUTPUT_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return HTTPException(status_code=404, detail="File not found")

@app.post("/clear_history")
async def clear_history():
    for folder in [config.INPUT_DIR, config.OUTPUT_DIR]:
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            if os.path.isfile(file_path):
                os.unlink(file_path)
    return JSONResponse({"status": "success"})

@app.post("/download_all")
async def download_all_as_zip():
    zip_filename = "Enhanced-Images.zip"
    zip_path = os.path.join(config.OUTPUT_DIR, zip_filename)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for filename in os.listdir(config.OUTPUT_DIR):
            if filename.lower().endswith('.png'):
                zipf.write(os.path.join(config.OUTPUT_DIR, filename), arcname=filename)
    return FileResponse(zip_path, filename=zip_filename, media_type="application/zip")