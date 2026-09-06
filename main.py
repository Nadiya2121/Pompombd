import os
import glob
import importlib.util
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from motor.motor_asyncio import AsyncIOMotorClient
from telegram.ext import Application
import uvicorn
import config

# MongoDB কানেকশন
client = AsyncIOMotorClient(config.MONGO_URI)
db = client.get_default_database("pompom_db")

app = FastAPI()
tg_app = Application.builder().token(config.BOT_TOKEN).build()

# মিনি অ্যাপ পেজ রেন্ডার
@app.get("/", response_class=HTMLResponse)
async def serve_home():
    with open("index.html", "r", encoding="utf-8") as f:
        content = f.read()
        # config থেকে নাম ডাইনামিকালি সেট করা হচ্ছে
        content = content.replace("{{APP_NAME}}", config.APP_NAME)
        return content

# প্লাগইন অটো-লোডার সিস্টেম
def load_plugins():
    plugin_files = glob.glob("plugins/*.py")
    for filepath in plugin_files:
        module_name = os.path.splitext(os.path.basename(filepath))[0]
        if module_name.startswith("__"):
            continue
        
        spec = importlib.util.spec_from_file_location(module_name, filepath)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # প্রতিটি প্লাগইনে থাকা setup() ফাংশন স্বয়ংক্রিয়ভাবে যুক্ত হবে
        if hasattr(module, "setup"):
            module.setup(app=app, tg_app=tg_app, db=db, config=config)
            print(f"🔌 [Plugin Activated]: {module_name}")

@app.on_event("startup")
async def on_startup():
    load_plugins()
    # ব্যাকগ্রাউন্ডে টেলিগ্রাম বট চালু
    await tg_app.initialize()
    await tg_app.start()
    await tg_app.updater.start_polling()
    print(f"🚀 {config.APP_NAME} Server & Bot Polling Started!")

@app.on_event("shutdown")
async def on_shutdown():
    await tg_app.updater.stop()
    await tg_app.stop()
    await tg_app.shutdown()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=config.PORT, reload=False)
