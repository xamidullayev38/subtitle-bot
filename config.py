import os
from pathlib import Path
from dotenv import load_dotenv

# .env faylini yuklash
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Asosiy sozlamalar
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "").strip()

# Yopiq saqlash kanali ID (Storage Channel)
storage_channel_raw = os.getenv("STORAGE_CHANNEL_ID", "0").strip()
try:
    if storage_channel_raw and not storage_channel_raw.startswith("-") and storage_channel_raw != "0":
        # Agar -100 siz kiritilgan bo'lsa, avtomatik qo'shamiz
        STORAGE_CHANNEL_ID = int(f"-100{storage_channel_raw}")
    else:
        STORAGE_CHANNEL_ID = int(storage_channel_raw)
except ValueError:
    STORAGE_CHANNEL_ID = 0

# Admin ID
admin_raw = os.getenv("ADMIN_ID", "0").strip()
try:
    ADMIN_ID = int(admin_raw)
except ValueError:
    ADMIN_ID = 0

# Vaqtinchalik fayllar papkasi
TEMP_DIR = BASE_DIR / "temp_files"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Ma'lumotlar bazasi fayli
DB_PATH = BASE_DIR / "movies.db"
