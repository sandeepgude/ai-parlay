from dotenv import load_dotenv
import os

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ODDS_API_KEY = os.getenv("ODDS_API_KEY")
