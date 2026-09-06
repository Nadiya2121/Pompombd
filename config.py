import os
from dotenv import load_dotenv

load_dotenv()

# অ্যাপের নাম (এখানে নাম পরিবর্তন করলেই পুরো মিনি অ্যাপ ও বটে স্বয়ংক্রিয়ভাবে বদলে যাবে)
APP_NAME = os.getenv("APP_NAME", "Pom Pom BD")

# সার্ভার পোর্ট (Render / Koyeb এর জন্য)
PORT = int(os.getenv("PORT", 8080))

# টেলিগ্রাম বট টোকেন (BotFather থেকে পাওয়া টোকেন)
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")

# MongoDB Atlas কানেকশন স্ট্রিং
MONGO_URI = os.getenv("MONGO_URI", "YOUR_MONGODB_ATLAS_URL")

# অ্যাডমিনের টেলিগ্রাম আইডি (কমা দিয়ে একাধিক অ্যাডমিন দেওয়া যাবে)
ADMIN_IDS = [int(i.strip()) for i in os.getenv("ADMIN_IDS", "123456789").split(",") if i.strip()]

# ডিফল্ট ইউটিউব স্টাইল (16:9) থাম্বনেইল
DEFAULT_THUMBNAIL = "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=1280&h=720&fit=crop"
