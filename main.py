import os
import glob
import threading
import importlib.util
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from motor.motor_asyncio import AsyncIOMotorClient
import telebot
import uvicorn
import config

# MongoDB কানেকশন
client = AsyncIOMotorClient(config.MONGO_URI)
db = client.get_default_database("pompom_db")

# টেলিগ্রাম বট
bot = telebot.TeleBot(config.BOT_TOKEN, parse_mode="Markdown", threaded=True)

def load_plugins():
    plugin_files = sorted(glob.glob("plugins/*.py"))
    for filepath in plugin_files:
        module_name = os.path.splitext(os.path.basename(filepath))[0]
        if module_name.startswith("__"):
            continue
        
        spec = importlib.util.spec_from_file_location(module_name, filepath)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        if hasattr(module, "setup"):
            module.setup(app=app, bot=bot, db=db, config=config)
            print(f"🔌 [Plugin Loaded]: {module_name}")

# সুপার স্টেবল ব্যাকগ্রাউন্ড বট পোলিং
def run_bot_polling():
    print(f"🤖 {config.APP_NAME} Bot Started Successfully!")
    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=20)
        except Exception as e:
            print(f"⚠️ Bot Connection Error: {e}, Retrying in 3 seconds...")
            import time
            time.sleep(3)

@asynccontextmanager
async def lifespan(app: FastAPI):
    load_plugins()
    # ডেডিকেটেড থ্রেডে বট চালু
    t = threading.Thread(target=run_bot_polling, daemon=True)
    t.start()
    yield

app = FastAPI(lifespan=lifespan)

# মিনি অ্যাপ ভিউ
@app.get("/", response_class=HTMLResponse)
async def serve_home():
    with open("index.html", "r", encoding="utf-8") as f:
        content = f.read()
        return content.replace("{{APP_NAME}}", config.APP_NAME)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=config.PORT, reload=False)
