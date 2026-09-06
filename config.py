import os
from dotenv import load_dotenv

load_dotenv()

# অ্যাপের নাম
APP_NAME = os.getenv("APP_NAME", "Pom Pom BD")

# আপনার Render বা Koyeb অ্যাপ লিঙ্ক
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://pompombd.onrender.com")

# ওয়েব অ্যাডমিন প্যানেলের সিকিউর পাসওয়ার্ড
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin1234")

# সার্ভার পোর্ট
PORT = int(os.getenv("PORT", 8080))

# টেলিগ্রাম বট টোকেন
BOT_TOKEN = os.getenv("BOT_TOKEN", "8933889793:AAE547Gis4FhQUJ0L9y0hCKo9U5m6XzhfcE")

# MongoDB Atlas URL
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://manogog673:manogog673@cluster0.ot1qt.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")

# অ্যাডমিনের টেলিগ্রাম আইডি
ADMIN_IDS = [int(i.strip()) for i in os.getenv("ADMIN_IDS", "8090888302").split(",") if i.strip()]

# ডিফল্ট 16:9 ভিডিও থাম্বনেইল
DEFAULT_THUMBNAIL = "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=1280&h=720&fit=crop"

# 🌟 নতুন: বটে /start দিলে যে ওয়েলকাম পোস্টার/ব্যানারটি শো করবে (যেকোনো ছবির লিঙ্ক এখানে বসাতে পারবেন)
WELCOME_POSTER = os.getenv(
    "WELCOME_POSTER", 
    "https://images.unsplash.com/photo-1579783902614-a3fb3927b675?w=1280&h=720&fit=crop"
)

# 🌟 নতুন: ওয়েলকাম মেসেজ টেক্সট
WELCOME_TEXT = os.getenv(
    "WELCOME_TEXT",
    "💋 **স্বাগতম Pom Pom BD বটে!** 🔥\n\n"
    "এখানে পাবেন সেরা ও চরম সব সেক্সি ভাইরাল ভিডিও কালেকশন! প্রতিদিন সবসময় একদম নতুন নতুন আপডেট ভিডিও দেখতে নিচের বাটনে ক্লিক করুন 👇"
)
