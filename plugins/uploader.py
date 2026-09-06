import threading
import requests
from pymongo import MongoClient
from telebot import types
from fastapi import Request

STATE = {}

def setup(app, bot, db, config):

    # স্টেবল এবং নন-ব্লকিং সিঙ্ক্রোনাস ডাটাবেজ কানেকশন
    sync_client = MongoClient(config.MONGO_URI)
    sync_db = sync_client.get_default_database("pompom_db")

    # ImgBB ক্লাউড ইমেজ আপলোড হেল্পার
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

    # ইউনিক সিরিজ কোড জেনারেটর (#101 থেকে শুরু)
    def get_next_series_code():
        last = sync_db.series.find_one(sort=[("code", -1)])
        if last and "code" in last:
            return last["code"] + 1
        return 101

    # =========================================================================
    # ১. ডিরেক্ট ভিডিও ডেলিভারি API (মিনি অ্যাপের টাইমার শেষ হতেই ভিডিও পাঠাবে)
    # =========================================================================
    @app.post("/api/deliver-video")
    async def deliver_video_api(req: Request):
        data = await req.json()
        part_id = data.get("part_id")
        user_id = data.get("user_id")

        if not part_id or not user_id:
            return {"status": "error", "message": "Missing parameters"}

        def send_file_task():
            try:
                from bson import ObjectId
                part = sync_db.video_parts.find_one({"_id": ObjectId(part_id)})
                if part:
                    bot.send_video(
                        chat_id=int(user_id),
                        video=part["file_id"],
                        caption=(
                            f"🎉 **আপনার আনলক করা ভিডিও:**\n\n"
                            f"📌 **সিরিজ:** {part.get('series_title', 'Video')}\n"
                            f"🔘 **পার্ট:** {part['button_text']}\n\n"
                            f"আমাদের সাথে থাকার জন্য ধন্যবাদ! ❤️"
                        )
                    )
            except Exception as e:
                print(f"Direct Delivery Error: {e}")

        threading.Thread(target=send_file_task).start()
        return {"status": "success"}

    # =========================================================================
    # ২. টেলিগ্রাম বট /start কমান্ড হ্যান্ডলার
    # =========================================================================
    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        chat_id = message.chat.id
        text = message.text or ""

        # যদি কোনো ইউজার ডিপলিংক দিয়ে ভিডিও নিতে আসে (যেমন: /start get_ID)
        if len(text.split()) > 1 and text.split()[1].startswith("get_"):
            part_id = text.split()[1].replace("get_", "")
            try:
                from bson import ObjectId
                part = sync_db.video_parts.find_one({"_id": ObjectId(part_id)})
                if part:
                    bot.send_video(
                        chat_id=chat_id,
                        video=part["file_id"],
                        caption=(
                            f"🎉 **আপনার আনলক করা ভিডিও:**\n\n"
                            f"📌 **সিরিজ:** {part.get('series_title', 'Video')}\n"
                            f"🔘 **পার্ট:** {part['button_text']}\n\n"
                            f"আমাদের সাথে থাকার জন্য ধন্যবাদ! ❤️"
                        )
                    )
                    return
            except Exception:
                pass

        # সাধারণ /start হলে আকর্ষণীয় ওয়েলকাম ব্যানার এবং ওপেন অ্যাপ বাটন
        markup = types.InlineKeyboardMarkup()
        btn = types.InlineKeyboardButton(
            text="🔥 Watch Now (ভিডিও দেখুন) 🔥",
            web_app=types.WebAppInfo(url=config.WEBAPP_URL)
        )
        markup.add(btn)

        try:
            bot.send_photo(
                chat_id=chat_id,
                photo=config.WELCOME_POSTER,
                caption=config.WELCOME_TEXT,
                reply_markup=markup
            )
        except Exception:
            bot.send_message(
                chat_id=chat_id,
                text=config.WELCOME_TEXT,
                reply_markup=markup
            )

    # =========================================================================
    # ৩. ভিডিও ফরওয়ার্ড/আপলোড হ্যান্ডলার (শুধু অ্যাডমিনের জন্য)
    # =========================================================================
    @bot.message_handler(content_types=['video'])
    def handle_video(message):
        user_id = message.from_user.id
        chat_id = message.chat.id

        if user_id not in config.ADMIN_IDS:
            return

        # প্রাইভেট DB চ্যানেলে ফাইল অটো-ফরওয়ার্ড ব্যাকআপ
        try:
            backup_msg = bot.forward_message(config.DB_CHANNEL_ID, chat_id, message.message_id)
            saved_file_id = backup_msg.video.file_id
        except Exception:
            saved_file_id = message.video.file_id

        STATE[chat_id] = {
            "file_id": saved_file_id,
            "step": "CHOOSE_TYPE"
        }

        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        markup.add("🆕 সম্পূর্ণ নতুন ভিডিও", "➕ আগের ভিডিওর পরবর্তী পার্ট")

        bot.send_message(
            chat_id,
            f"🎬 **ভিডিও পাওয়া গেছে!**\n\nএটি কি কোনো নতুন ভিডিও, নাকি আগের কোনো ভিডিওর পরবর্তী পার্ট?",
            reply_markup=markup
        )

    # =========================================================================
    # ৪. স্টেপ বাই স্টেপ টেক্সট ইনপুট হ্যান্ডলার
    # =========================================================================
    @bot.message_handler(func=lambda msg: msg.chat.id in STATE and msg.text)
    def handle_admin_inputs(message):
        chat_id = message.chat.id
        user_id = message.from_user.id

        if user_id not in config.ADMIN_IDS:
            return

        step = STATE[chat_id].get("step")
        text = message.text.strip()

        # ধাপ ক: নতুন সিরিজ নাকি পুরনো সিরিজ নির্বাচন
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

        # ধাপ খ: পুরনো ভিডিওর কোড দিয়ে ডাটাবেজ থেকে খুঁজে বের করা
        if step == "AWAIT_CODE":
            if not text.isdigit():
                bot.send_message(chat_id, "❌ শুধুমাত্র সংখ্যায় কোড দিন (যেমন: 101):")
                return
            code = int(text)
            series = sync_db.series.find_one({"code": code})
            if not series:
                bot.send_message(chat_id, f"❌ কোড #{code} এর কোনো ভিডিও পাওয়া যায়নি! আবার সঠিক কোড দিন:")
                return
            
            STATE[chat_id]["parent_id"] = series["_id"]
            STATE[chat_id]["series_title"] = series["title"]
            STATE[chat_id]["step"] = "AWAIT_PART_NUM"
            bot.send_message(
                chat_id,
                f"✅ ভিডিও পাওয়া গেছে: **{series['title']}**\n\nএখন শুধু **পার্ট নম্বর** লিখে পাঠান (যেমন: 2 বা 3):"
            )
            return

        # ধাপ গ: নতুন সিরিজের টাইটেল গ্রহণ করা
        if step == "AWAIT_TITLE":
            STATE[chat_id]["title"] = text
            STATE[chat_id]["step"] = "AWAIT_THUMB"
            bot.send_message(
                chat_id,
                "✅ টাইটেল সেট হয়েছে!\n\nএখন ভিডিওর **পোস্টার/থাম্বনেইল (Photo)** পাঠান (না থাকলে /skip লিখুন):"
            )
            return

        # ধাপ ঘ: থাম্বনেইল স্কিপ করলে
        if step == "AWAIT_THUMB" and text.lower() == "/skip":
            STATE[chat_id]["thumbnail"] = config.DEFAULT_THUMBNAIL
            STATE[chat_id]["step"] = "AWAIT_PART_NUM"
            bot.send_message(
                chat_id,
                "⏩ থাম্বনেইল স্কিপ হয়েছে।\n\nএখন শুধু **পার্ট নম্বর** লিখে দিন (যেমন: শুধু 1 লিখলেই হবে):"
            )
            return

        # ধাপ ঙ: পার্ট নম্বর নিয়ে ডাটাবেজে পার্মানেন্ট সেভ
        if step == "AWAIT_PART_NUM":
            part_clean = text.replace("Part", "").replace("part", "").strip()
            button_name = f"🎬 Video Part {part_clean}" if part_clean.isdigit() else text
            data = STATE[chat_id]
            del STATE[chat_id]

            try:
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
                    series_id = data["parent_id"]
                    series_title = data["series_title"]
                    series_obj = sync_db.series.find_one({"_id": series_id})
                    code_display = f"#{series_obj.get('code', 'N/A')}"

                # ভিডিও পার্ট সেভ
                sync_db.video_parts.insert_one({
                    "series_id": series_id,
                    "series_title": series_title,
                    "file_id": data["file_id"],
                    "button_text": button_name,
                    "clicks": 0
                })

                bot.send_message(
                    chat_id,
                    f"🎉 **সফলভাবে সেভ হয়েছে!**\n\n"
                    f"🔢 **সিরিজ কোড:** {code_display}\n"
                    f"📌 **ভিডিওর নাম:** {series_title}\n"
                    f"🔘 **বাটন:** {button_name}\n\n"
                    f"🌐 মিনি অ্যাপ এবং অ্যাডমিন প্যানেলে ভিডিওটি এখন লাইভ!"
                )
            except Exception as e:
                bot.send_message(chat_id, f"❌ সেভ করতে ত্রুটি হয়েছে: {str(e)}")

    # =========================================================================
    # ৫. থাম্বনেইল ছবি হ্যান্ডলার
    # =========================================================================
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
