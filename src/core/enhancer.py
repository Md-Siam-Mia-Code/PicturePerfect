# src/core/enhancer.py
import os
import logging
import requests
import time
import torch
from basicsr.archs.rrdbnet_arch import RRDBNet
from gfpgan import GFPGANer
from realesrgan import RealESRGANer
from requests.adapters import Retry, HTTPAdapter
from requests.exceptions import RequestException

class PicturePerfectEnhancer:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.gfpganer = None
        self.bg_upsampler = None
        self.is_initialized = False
        self.logger.info(f"ℹ️  Enhancer initialized on device: {self.device}")

    def check_models(self):
        """Checks for all required models and returns a list of missing ones."""
        missing_models = []
        for name, filename, url, dest_dir in self.config.REQUIRED_MODELS:
            path = os.path.join(dest_dir, filename)
            if not os.path.exists(path):
                missing_models.append({"name": name, "filename": filename, "url": url})
        return missing_models

    def download_model(self, model_info):
        """A generator that downloads a single model and yields progress."""
        name = model_info['name']
        url = model_info['url']
        filename = model_info['filename']
        dest_dir = next((m[3] for m in self.config.REQUIRED_MODELS if m[0] == name), None)
        if not dest_dir: raise ValueError(f"Unknown model name: {name}")

        os.makedirs(dest_dir, exist_ok=True)
        destination = os.path.join(dest_dir, filename)

        self.logger.info(f"⬇️  Downloading {name} from {url}...")

        if os.path.exists(destination):
            self.logger.info(f"   - Cleaning up previous incomplete download for {name}.")
            os.remove(destination)
        
        session = requests.Session()
        retry_strategy = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)

        try:
            response = session.get(url, stream=True, timeout=20)
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            with open(destination, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    progress = (downloaded_size / total_size) * 100 if total_size > 0 else 0
                    yield {"status": "downloading", "model_name": name, "progress": progress}
            
            self.logger.info(f"✅ Download complete for {name}.")
            yield {"status": "completed", "model_name": name}

        except RequestException as e:
            self.logger.error(f"❌ Download failed for {name}: {e}")
            if os.path.exists(destination):
                os.remove(destination)
            yield {"status": "error", "model_name": name, "error_message": str(e)}

    def load_models_into_memory(self):
        """Loads the models into the GPU/CPU memory after they are downloaded."""
        if self.is_initialized:
            return

        self.logger.info(f"🧠 Loading models into memory on device: {self.device}")
        
        realesrgan_model_path = next(os.path.join(m[3], m[1]) for m in self.config.REQUIRED_MODELS if m[0] == "Real-ESRGAN x4+")
        bg_model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
        self.bg_upsampler = RealESRGANer(
            scale=4, model_path=realesrgan_model_path, model=bg_model, tile=400,
            tile_pad=10, pre_pad=0, half=self.config.USE_HALF_PRECISION, device=self.device
        )
        
        gfpgan_model_path = next(os.path.join(m[3], m[1]) for m in self.config.REQUIRED_MODELS if m[0] == "GFPGAN v1.4")
        self.gfpganer = GFPGANer(
            model_path=gfpgan_model_path, upscale=self.config.UPSCALE_FACTOR,
            arch=self.config.ARCH, channel_multiplier=2, bg_upsampler=self.bg_upsampler,
            device=self.device
        )
        
        self.is_initialized = True
        self.logger.info("✅ All models loaded and ready to enhance.")

    def enhance(self, image, upscale_factor: int):
        if not self.is_initialized:
            raise RuntimeError("Models are not loaded. Please ensure all models are downloaded and loaded first.")
        self.gfpganer.upscale = upscale_factor
        try:
            _, _, restored_img = self.gfpganer.enhance(
                image, has_aligned=False, only_center_face=False, paste_back=True, weight=0.5
            )
            return restored_img
        except Exception as e:
            self.logger.error(f"❌ An error occurred during enhancement: {e}", exc_info=True)
            raise e

    def get_system_info(self):
        """Returns basic system and model status info."""
        return {
            "gpu_detected": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
            "half_precision": self.config.USE_HALF_PRECISION,
            "models_loaded": self.is_initialized
        }