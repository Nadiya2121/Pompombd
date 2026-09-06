import os
from dotenv import load_dotenv

load_dotenv()

# অ্যাপের নাম
APP_NAME = os.getenv("APP_NAME", "Pom Pom BD")

# আপনার Render বা Koyeb অ্যাপ লিঙ্ক
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://your-app-name.onrender.com")

# ওয়েব অ্যাডমিন প্যানেলের সিকিউর পাসওয়ার্ড (এখানে আপনার পছন্দের পাসওয়ার্ড দিন)
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin1234")

# সার্ভার পোর্ট
PORT = int(os.getenv("PORT", 8080))

# টেলিগ্রাম বট টোকেন
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")

# MongoDB Atlas URL
MONGO_URI = os.getenv("MONGO_URI", "YOUR_MONGODB_ATLAS_URL")

# অ্যাডমিনের টেলিগ্রাম আইডি
ADMIN_IDS = [int(i.strip()) for i in os.getenv("ADMIN_IDS", "123456789").split(",") if i.strip()]

# ডিফল্ট 16:9 থাম্বনেইল
DEFAULT_THUMBNAIL = "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=1280&h=720&fit=crop"
