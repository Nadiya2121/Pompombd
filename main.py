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

# MongoDB ক্লাউড কানেকশন
client = AsyncIOMotorClient(config.MONGO_URI)
db = client.get_default_database("pompom_db")

# টেলিগ্রাম বট
bot = telebot.TeleBot(config.BOT_TOKEN, parse_mode="Markdown")

# প্লাগইন লোডার ফাংশন
def load_plugins():
    plugin_files = sorted(glob.glob("plugins/*.py"))
    for filepath in plugin_files:
        module_name = os.path.splitext(os.path.basename(filepath))[0]
        if module_name.startswith("__"):
            continue
        
        spec = importlib.util.spec_from_file_location(module_name, filepath)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # প্রতিটি প্লাগইনে ঠিকঠাক আর্গুমেন্ট পাঠানো
        if hasattr(module, "setup"):
            module.setup(app=app, bot=bot, db=db, config=config)
            print(f"🔌 [Plugin Loaded]: {module_name}")

def start_bot():
    print(f"🤖 {config.APP_NAME} Bot is Polling...")
    try:
        bot.infinity_polling(skip_pending=True)
    except Exception as e:
        print(f"Bot Polling Error: {e}")

# আধুনিক FastAPI Lifespan (কোনো Deprecation Warning আসবে না)
@asynccontextmanager
async def lifespan(app: FastAPI):
    load_plugins()
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()
    yield

app = FastAPI(lifespan=lifespan)

# মিনি অ্যাপ পেজ রেন্ডার
@app.get("/", response_class=HTMLResponse)
async def serve_home():
    with open("index.html", "r", encoding="utf-8") as f:
        content = f.read()
        return content.replace("{{APP_NAME}}", config.APP_NAME)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=config.PORT, reload=False)
