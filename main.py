import os
import glob
import threading
import importlib.util
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from motor.motor_asyncio import AsyncIOMotorClient
import telebot
import uvicorn
import config

# MongoDB ক্লাউড ডাটাবেজ
client = AsyncIOMotorClient(config.MONGO_URI)
db = client.get_default_database("pompom_db")

# FastAPI সার্ভার ও টেলিগ্রাম বট ইনিট
app = FastAPI()
bot = telebot.TeleBot(config.BOT_TOKEN, parse_mode="Markdown")

# হোমপেজ / মিনি অ্যাপ রেন্ডার
@app.get("/", response_class=HTMLResponse)
async def serve_home():
    with open("index.html", "r", encoding="utf-8") as f:
        content = f.read()
        return content.replace("{{APP_NAME}}", config.APP_NAME)

# প্লাগইন লোডার
def load_plugins():
    plugin_files = glob.glob("plugins/*.py")
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

# টেলিগ্রাম বট ব্যাকগ্রাউন্ড থ্রেডে চালু করা (যাতে কোনো ব্লকিং না হয়)
def start_bot():
    print(f"🤖 {config.APP_NAME} Bot is Polling...")
    try:
        bot.infinity_polling(skip_pending=True)
    except Exception as e:
        print(f"Bot Polling Error: {e}")

@app.on_event("startup")
async def on_startup():
    load_plugins()
    # বট থ্রেড রান
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=config.PORT, reload=False)
