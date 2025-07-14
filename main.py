# main.py
import uvicorn
import os
import logging
import sys
import config
from src.web.app import app

# --- Enhanced Logging Setup ---
def setup_logging():
    """
    Configures a clean logger that focuses on application-specific messages
    and suppresses noise from underlying libraries.
    """
    # Define a clear and concise format for our logs
    LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
    
    # Configure the root logger
    logging.basicConfig(
        level=config.LOG_LEVEL,
        format=LOG_FORMAT,
        stream=sys.stdout  # Ensure logs go to the console
    )

    # Aggressively suppress logs from noisy third-party libraries
    noisy_libraries = [
        "uvicorn", "uvicorn.error", "uvicorn.access",
        "fastapi", "websockets", "httpx", "asyncio", "PIL"
    ]
    for lib_name in noisy_libraries:
        logging.getLogger(lib_name).setLevel(logging.ERROR)

# --- Main Application Entry Point ---
def main():
    """
    The main function that prepares and runs the PicturePerfect application.
    """
    # 1. Configure our custom logger first
    setup_logging()
    logger = logging.getLogger(__name__)

    # 2. Print a beautiful startup banner
    logger.info("======================================================")
    logger.info("        🚀 Welcome to PicturePerfect v2.0 🚀         ")
    logger.info("======================================================")

    # 3. Prepare necessary directories
    logger.info("📂 Preparing required directories...")
    try:
        os.makedirs(config.INPUT_DIR, exist_ok=True)
        os.makedirs(config.OUTPUT_DIR, exist_ok=True)
        os.makedirs(config.GFPGAN_MODEL_DIR, exist_ok=True)
        os.makedirs(config.REALESRGAN_MODEL_DIR, exist_ok=True)
        logger.info("✅ Directories are ready.")
    except Exception as e:
        logger.error(f"❌ Failed to create directories: {e}")
        sys.exit(1)

    # 4. Announce server startup
    logger.info("🌐 Starting the web server...")
    logger.info(f"✅ Server is live! Access the UI at: http://{config.SERVER_HOST}:{config.SERVER_PORT}")
    logger.info("   (Press CTRL+C to stop the server)")
    
    # 5. Run the Uvicorn server
    uvicorn.run(
        app,
        host=config.SERVER_HOST,
        port=config.SERVER_PORT,
        log_config=None  # IMPORTANT: Disable Uvicorn's default logger to use our own
    )

if __name__ == "__main__":
    main()