from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
EXTRACTED_IMAGES_DIR = DATA_DIR / "extracted_images"
EXTRACTED_AUDIO_DIR = DATA_DIR / "extracted_audio"
EXTRACTED_FRAMES_DIR = DATA_DIR / "extracted_frames"
DB_PATH = DATA_DIR / "global_stats.sqlite"

# Ensure runtime directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
EXTRACTED_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
EXTRACTED_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
EXTRACTED_FRAMES_DIR.mkdir(parents=True, exist_ok=True)

# Ollama Models & Options (Mandatory Hardware Constraints)
OLLAMA_BASE_URL = "http://localhost:11434"

# Vision & Chat Model: qwen2.5vl:7b on GPU with 8k context
VISION_MODEL = "qwen2.5vl:7b"
VISION_OPTIONS = {
    "num_ctx": 8192
}

# Embedding Model: embeddinggemma-2:latest explicitly on CPU/RAM to protect VRAM
EMBEDDING_MODEL = "embeddinggemma-2:latest"
EMBEDDING_OPTIONS = {
    "num_gpu": 0
}

# Qdrant Vector DB Configuration
QDRANT_HOST = "127.0.0.1"
QDRANT_PORT = 6333
QDRANT_COLLECTION = "pdf_multimodal_rag"

# Extraction Filters (discard small logos, icons, decorative lines)
MIN_IMAGE_WIDTH = 120
MIN_IMAGE_HEIGHT = 120
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150

# Audio & Video Processing Configuration
AUDIO_CHUNK_DURATION = 15.0  # seconds per audio transcription slice
VIDEO_FRAME_INTERVAL = 10.0  # seconds between representative video keyframes
MAX_VIDEO_FRAMES = 24        # maximum visual frames to analyze per video
