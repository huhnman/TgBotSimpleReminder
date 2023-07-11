from dotenv import load_dotenv
import os

load_dotenv()
BOT_API_KEY = os.environ.get('BOT_API_KEY')
APS_TIMEZONE = os.environ.get('APS_TIMEZONE')
