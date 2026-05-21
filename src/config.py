import os
from pathlib import Path

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
IMAGES_DIR = DATA_DIR / "images"
DB_PATH = DATA_DIR / "pokedex.db"
DLQ_PATH = DATA_DIR / "dlq_falhas_banco.json"
