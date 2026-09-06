import os
import sys
from dotenv import load_dotenv

# লোকাল টেস্টের জন্য .env ফাইল থাকলে লোড করবে
load_dotenv()

# ১. অ্যাপের নাম (Environment না পেলে ডিফল্ট 'Pom Pom BD' নেবে)
APP_NAME = os.getenv("APP_NAME", "Pom Pom BD")

# ২. সার্ভার পোর্ট (Render/Koyeb স্বয়ংক্রিয়ভাবে পোর্ট দেয়)
PORT = int(os.getenv("PORT", 8080))

# ৩. টেলিগ্রাম বট টোকেন (সরাসরি Environment থেকে আসবে)
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ৪. MongoDB কানেকশন স্ট্রিং (সরাসরি Environment থেকে আসবে)
MONGO_URI = os.getenv("MONGO_URI")

# ৫. অ্যাডমিনের টেলিগ্রাম আইডি (Environment থেকে আসবে, কমা দিয়ে একাধিক দেওয়া যাবে)
admin_ids_raw = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(i.strip()) for i in admin_ids_raw.split(",") if i.strip().isdigit()]

# ৬. আপনার ডিপ্লয় করা সাইটের URL (যেমন: https://pompom-bd.onrender.com)
WEBAPP_URL = os.getenv("WEBAPP_URL", "")

# ৭. ওয়েব অ্যাডমিন প্যানেলের পাসওয়ার্ড
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin1234")

# ৮. ইউটিউব সাইজ (16:9) ডিফল্ট পোস্টার থাম্বনেইল
DEFAULT_THUMBNAIL = os.getenv(
    "DEFAULT_THUMBNAIL",
    "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=1280&h=720&fit=crop"
)

# ৯. ওয়েলকাম ব্যানার পোস্টার লিঙ্ক
WELCOME_POSTER = os.getenv(
    "WELCOME_POSTER",
    "https://images.unsplash.com/photo-1579783902614-a3fb3927b675?w=1280&h=720&fit=crop"
)

# ১০. ওয়েলকাম টেক্সট মেসেজ
WELCOME_TEXT = os.getenv(
    "WELCOME_TEXT",
    "💋 **স্বাগতম Pom Pom BD বটে!** 🔥\n\n"
    "এখানে পাবেন সেরা ও চরম সব সেক্সি ভাইরাল ভিডিও কালেকশন! প্রতিদিন সবসময় একদম নতুন নতুন আপডেট ভিডিও দেখতে নিচের বাটনে ক্লিক করুন 👇"
)

# জরুরি সিকিউরিটি চেক: BOT_TOKEN বা MONGO_URI না দিলে সার্ভার পরিষ্কার এরর মেসেজ দেবে
if not BOT_TOKEN:
    print("❌ ERROR: 'BOT_TOKEN' Environment Variable সেট করা হয়নি!")
    sys.exit(1)

if not MONGO_URI:
    print("❌ ERROR: 'MONGO_URI' Environment Variable সেট করা হয়নি!")
    sys.exit(1)
