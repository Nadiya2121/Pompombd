import threading
import requests
from pymongo import MongoClient
from telebot import types

STATE = {}

def setup(app, bot, db, config):

    # সরাসরি সিঙ্ক্রোনাস ক্লায়েন্ট (থ্রেড ক্র্যাশ ও হ্যাং হওয়া বন্ধ করবে)
    sync_client = MongoClient(config.MONGO_URI)
    sync_db = sync_client.get_default_database("pompom_db")

    # ImgBB তে ইমেজ আপলোড
    def upload_to_imgbb(file_path):
        try:
            if not config.IMGBB_API_KEY or config.IMGBB_API_KEY == "your_imgbb_api_key_here":
                return config.DEFAULT_THUMBNAIL
            with open(file_path, "rb") as file:
                res = requests.post(
                    "https://api.imgbb.com/1/upload",
                    data={"key": config.IMGBB_API_KEY},
                    files={"image": file}
                )
                data = res.json()
                if data.get("success"):
                    return data["data"]["url"]
        except Exception:
            pass
        return config.DEFAULT_THUMBNAIL

    # অটোমেটিক ইউনিক সিরিয়াল কোড জেনারেটর (101 থেকে শুরু হবে)
    def get_next_series_code():
        last = sync_db.series.find_one(sort=[("code", -1)])
        if last and "code" in last:
            return last["code"] + 1
        return 101

    # ১. /start কমান্ড
    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        chat_id = message.chat.id
        text = message.text or ""

        # ইউজার আনলক করে ভিডিও নিতে আসলে
        if len(text.split()) > 1 and text.split()[1].startswith("get_"):
            part_id = text.split()[1].replace("get_", "")
            try:
                from bson import ObjectId
                part = sync_db.video_parts.find_one({"_id": ObjectId(part_id)})
                if part:
                    bot.send_video(
                        chat_id=chat_id,
                        video=part["file_id"],
                        caption=f"🎉 **আপনার আনলক করা ভিডিও:**\n\n📌 {part.get('series_title', 'Video')} - {part['button_text']}\n\nধন্যবাদ আমাদের সাথে থাকার জন্য! ❤️"
                    )
                else:
                    bot.send_message(chat_id, "❌ দুঃখিত, ভিডিওটি পাওয়া যায়নি!")
            except Exception as e:
                bot.send_message(chat_id, f"❌ ত্রুটি: {str(e)}")
            return

        # সাধারণ /start হলে
        markup = types.InlineKeyboardMarkup()
        btn = types.InlineKeyboardButton(
            text="🔥 Watch Now (ভিডিও দেখুন) 🔥",
            web_app=types.WebAppInfo(url=config.WEBAPP_URL)
        )
        markup.add(btn)

        try:
            bot.send_photo(chat_id=chat_id, photo=config.WELCOME_POSTER, caption=config.WELCOME_TEXT, reply_markup=markup)
        except Exception:
            bot.send_message(chat_id, config.WELCOME_TEXT, reply_markup=markup)

    # ২. অ্যাডমিন ভিডিও পাঠালে
    @bot.message_handler(content_types=['video'])
    def handle_video(message):
        user_id = message.from_user.id
        chat_id = message.chat.id

        if user_id not in config.ADMIN_IDS:
            return

        # DB চ্যানেলে ব্যাকআপ
        try:
            backup_msg = bot.forward_message(config.DB_CHANNEL_ID, chat_id, message.message_id)
            saved_file_id = backup_msg.video.file_id
        except Exception:
            saved_file_id = message.video.file_id

        STATE[chat_id] = {
            "file_id": saved_file_id,
            "step": "CHOOSE_TYPE"
        }

        # নতুন সিরিজ নাকি আগের পার্ট সিলেক্ট করার অপশন
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        markup.add("🆕 সম্পূর্ণ নতুন ভিডিও", "➕ আগের ভিডিওর পরবর্তী পার্ট")

        bot.send_message(
            chat_id,
            f"🎬 **ভিডিও পাওয়া গেছে!**\n\nএটি কি কোনো নতুন ভিডিও, নাকি আগের কোনো ভিডিওর পরবর্তী পার্ট?",
            reply_markup=markup
        )

    # ৩. স্টেপ বাই স্টেপ টেক্সট হ্যান্ডলার
    @bot.message_handler(func=lambda msg: msg.chat.id in STATE and msg.text)
    def handle_admin_inputs(message):
        chat_id = message.chat.id
        user_id = message.from_user.id

        if user_id not in config.ADMIN_IDS:
            return

        step = STATE[chat_id].get("step")
        text = message.text.strip()

        # ধাপ ক: ভিডিওর ধরন বাছাই
        if step == "CHOOSE_TYPE":
            if "নতুন" in text:
                STATE[chat_id]["is_new"] = True
                STATE[chat_id]["step"] = "AWAIT_TITLE"
                bot.send_message(
                    chat_id, 
                    "📝 এখন **ভিডিওর একটি সুন্দর টাইটেল/নাম** লিখে পাঠান:",
                    reply_markup=types.ReplyKeyboardRemove()
                )
            elif "আগের" in text:
                STATE[chat_id]["is_new"] = False
                STATE[chat_id]["step"] = "AWAIT_CODE"
                bot.send_message(
                    chat_id, 
                    "🔢 আগের ভিডিওটির **ইউনিক কোড** নম্বরটি দিন (যেমন: 101, 102):",
                    reply_markup=types.ReplyKeyboardRemove()
                )
            return

        # ধাপ খ (পুরনো ভিডিওর জন্য): কোড দিয়ে মূল ভিডিও খোঁজা
        if step == "AWAIT_CODE":
            if not text.isdigit():
                bot.send_message(chat_id, "❌ শুধুমাত্র সংখ্যায় কোড দিন (যেমন: 101):")
                return
            
            code = int(text)
            series = sync_db.series.find_one({"code": code})
            if not series:
                bot.send_message(chat_id, f"❌ কোড #{code} এর কোনো ভিডিও খুঁজে পাওয়া যায়নি! আবার সঠিক কোড দিন:")
                return
            
            STATE[chat_id]["parent_id"] = series["_id"]
            STATE[chat_id]["series_title"] = series["title"]
            STATE[chat_id]["step"] = "AWAIT_PART_NUM"
            bot.send_message(
                chat_id, 
                f"✅ ভিডিও পাওয়া গেছে: **{series['title']}**\n\nএখন শুধু **পার্ট নম্বর** লিখে পাঠান (যেমন: 2 বা 3):"
            )
            return

        # ধাপ গ (নতুন ভিডিওর জন্য): টাইটেল গ্রহণ
        if step == "AWAIT_TITLE":
            STATE[chat_id]["title"] = text
            STATE[chat_id]["step"] = "AWAIT_THUMB"
            bot.send_message(
                chat_id, 
                "✅ টাইটেল সেট হয়েছে!\n\nএখন ভিডিওর **পোস্টার/থাম্বনেইল (Photo)** পাঠান (না থাকলে /skip লিখুন):"
            )
            return

        # ধাপ ঘ (নতুন ভিডিওর জন্য): থাম্বনেইল স্কিপ করলে
        if step == "AWAIT_THUMB" and text.lower() == "/skip":
            STATE[chat_id]["thumbnail"] = config.DEFAULT_THUMBNAIL
            STATE[chat_id]["step"] = "AWAIT_PART_NUM"
            bot.send_message(
                chat_id, 
                "⏩ থাম্বনেইল স্কিপ হয়েছে।\n\nএখন শুধু **পার্ট নম্বর** লিখে দিন (যেমন: শুধু 1 লিখলেই হবে):"
            )
            return

        # ধাপ ঙ: পার্ট নম্বর পেয়ে সেভ করা (মেইন লজিক)
        if step == "AWAIT_PART_NUM":
            # স্মার্ট বাটন ফরম্যাট: ইউজার '1' দিলে হয়ে যাবে '🎬 Video Part 1'
            part_clean = text.replace("Part", "").replace("part", "").strip()
            if part_clean.isdigit():
                button_name = f"🎬 Video Part {part_clean}"
            else:
                button_name = text  # যদি নিজে কোনো নাম লিখতে চায়

            data = STATE[chat_id]
            del STATE[chat_id]

            try:
                # নতুন সিরিজ হলে আগে সিরিজ তৈরি হবে
                if data.get("is_new"):
                    new_code = get_next_series_code()
                    series_id = sync_db.series.insert_one({
                        "code": new_code,
                        "title": data["title"],
                        "thumbnail": data.get("thumbnail", config.DEFAULT_THUMBNAIL),
                        "views": 0
                    }).inserted_id
                    series_title = data["title"]
                    code_display = f"#{new_code}"
                else:
                    # পুরনো সিরিজ হলে
                    series_id = data["parent_id"]
                    series_title = data["series_title"]
                    series_obj = sync_db.series.find_one({"_id": series_id})
                    code_display = f"#{series_obj.get('code', 'N/A')}"

                # পার্ট সেভ করা
                sync_db.video_parts.insert_one({
                    "series_id": series_id,
                    "series_title": series_title,
                    "file_id": data["file_id"],
                    "button_text": button_name,
                    "clicks": 0
                })

                # সফলভাবে কনফার্মেশন মেসেজ
                bot.send_message(
                    chat_id,
                    f"🎉 **সফলভাবে সেভ হয়েছে!**\n\n"
                    f"🔢 **ইউনিক কোড:** {code_display}\n"
                    f"📌 **ভিডিওর নাম:** {series_title}\n"
                    f"🔘 **বাটন নাম:** {button_name}\n\n"
                    f"💡 পরবর্তীতে এই ভিডিওতে নতুন পার্ট যোগ করতে কোড {code_display} ব্যবহার করুন।"
                )
            except Exception as e:
                bot.send_message(chat_id, f"❌ সেভ করতে সমস্যা হয়েছে: {str(e)}")

    # ৪. থাম্বনেইল ছবি পাঠানো হলে
    @bot.message_handler(content_types=['photo'])
    def handle_thumbnail(message):
        chat_id = message.chat.id
        user_id = message.from_user.id

        if user_id not in config.ADMIN_IDS or chat_id not in STATE:
            return

        if STATE[chat_id].get("step") == "AWAIT_THUMB":
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded = bot.download_file(file_info.file_path)

            temp_path = f"thumb_{chat_id}.jpg"
            with open(temp_path, 'wb') as f:
                f.write(downloaded)

            bot.send_message(chat_id, "⏳ থাম্বনেইল ImgBB ক্লাউডে আপলোড হচ্ছে...")
            cdn_url = upload_to_imgbb(temp_path)

            STATE[chat_id]["thumbnail"] = cdn_url
            STATE[chat_id]["step"] = "AWAIT_PART_NUM"
            bot.send_message(
                chat_id, 
                "✅ থাম্বনেইল ক্লাউডে সেভ হয়েছে!\n\nএবার শুধু **পার্ট নম্বর** লিখে পাঠান (যেমন: শুধু 1 লিখলেই হবে):"
            )
