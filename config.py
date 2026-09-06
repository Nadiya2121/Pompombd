import os
import sys
from dotenv import load_dotenv

load_dotenv()

# ========================================================
# ক) Environment Variables (Render/Koyeb থেকে আসবে)
# ========================================================
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
WEBAPP_URL = os.getenv("WEBAPP_URL", "")
admin_ids_raw = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(i.strip()) for i in admin_ids_raw.split(",") if i.strip().isdigit()]

# ১. প্রাইভেট ডাটাবেজ চ্যানেল আইডি (যেমন: -1001234567890)
DB_CHANNEL_ID = int(os.getenv("DB_CHANNEL_ID", "-1003852261982"))

# ২. ImgBB API Key (https://api.imgbb.com থেকে ফ্রি পাওয়া যায়)
IMGBB_API_KEY = os.getenv("IMGBB_API_KEY", "3afad85f951cbc60f3c0d7cb3bc6f268")

# সার্ভার পোর্ট
PORT = int(os.getenv("PORT", 8080))

# ========================================================
# খ) ব্র্যান্ডিং ও কনফিগারেশন
# ========================================================
APP_NAME = "Pom Pom BD"
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin1234")

DEFAULT_THUMBNAIL = "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=1280&h=720&fit=crop"

WELCOME_POSTER = os.getenv(
    "WELCOME_POSTER",
    "https://images.unsplash.com/photo-1579783902614-a3fb3927b675?w=1280&h=720&fit=crop"
)

WELCOME_TEXT = (
    "💋 **স্বাগতম Pom Pom BD বটে!** 🔥\n\n"
    "এখানে পাবেন সেরা ও চরম সব সেক্সি ভাইরাল ভিডিও কালেকশন! প্রতিদিন সবসময় একদম নতুন নতুন আপডেট ভিডিও দেখতে নিচের বাটনে ক্লিক করুন 👇"
)

# সিকিউরিটি চেক
if not BOT_TOKEN:
    print("❌ ERROR: 'BOT_TOKEN' বসানো হয়নি!")
    sys.exit(1)

if not MONGO_URI:
    print("❌ ERROR: 'MONGO_URI' বসানো হয়নি!")
    sys.exit(1)
