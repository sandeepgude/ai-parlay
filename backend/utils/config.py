from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

# ================================
# 🔑 API KEYS
# ================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY_2", "")
ODDS_API_KEY = os.getenv("ODDS_API_KEY", "")
BALLDONTLIE_KEY = os.getenv("BALLDONTLIE_KEY", "")

# ================================
# 🏀 BallDontLie API Config
# ================================
BALLDONTLIE_BASE = "https://api.balldontlie.io/v1"

BALLDONTLIE_HEADERS = {
    "Authorization": f"Bearer {BALLDONTLIE_KEY}"
}

# ================================
# 🔍 Debug Logging (Optional)
# ================================
if not OPENAI_API_KEY:
    print("⚠️ OPENAI_API_KEY_2 missing in .env")

if not ODDS_API_KEY:
    print("⚠️ ODDS_API_KEY missing in .env")

if not BALLDONTLIE_KEY:
    print("⚠️ BALLDONTLIE_KEY missing in .env")
