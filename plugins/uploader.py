import threading
import requests
from telebot import types

STATE = {}

def setup(app, bot, db, config):

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

    # ১. /start হ্যান্ডলার (সাধারণ ইউজার ও ভিডিও ডেলিভারি রিকোয়েস্ট)
    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        chat_id = message.chat.id
        text = message.text

        # যদি ইউজার অ্যাড শেষ করে ভিডিওর লিংক দিয়ে ইনবক্সে আসে (যেমন: /start get_VIDEOID)
        if len(text.split()) > 1 and text.split()[1].startswith("get_"):
            video_part_id = text.split()[1].replace("get_", "")
            
            def send_file_worker():
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                async def deliver():
                    from bson import ObjectId
                    part = await db.video_parts.find_one({"_id": ObjectId(video_part_id)})
                    if part:
                        bot.send_video(
                            chat_id=chat_id,
                            video=part["file_id"],
                            caption=f"🎉 **আপনার আনলক করা ভিডিও:**\n\n📌 {part['title']} ({part['button_text']})\n\nধন্যবাদ আমাদের সাথে থাকার জন্য! ❤️"
                        )
                    else:
                        bot.send_message(chat_id, "❌ দুঃখিত, ভিডিওটি খুঁজে পাওয়া যায়নি!")
                loop.run_until_complete(deliver())
                loop.close()

            threading.Thread(target=send_file_worker).start()
            return

        # সাধারণ /start হলে ওয়েলকাম ব্যানার ও মিনি অ্যাপ বাটন
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

    # ২. ধাপ ক: অ্যাডমিন ভিডিও ফরওয়ার্ড করলে
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
            "step": "AWAIT_TITLE",
            "file_id": saved_file_id
        }
        bot.send_message(chat_id, f"🎬 **[{config.APP_NAME}] ভিডিও পাওয়া গেছে!**\n\nএখন দয়া করে **ভিডিওর টাইটেল/নাম** লিখে পাঠান:")

    # ৩. ধাপ খ ও ঘ: টেক্সট হ্যান্ডলার (টাইটেল এবং বাটন নেম)
    @bot.message_handler(func=lambda msg: msg.chat.id in STATE and msg.text)
    def handle_text(message):
        chat_id = message.chat.id
        user_id = message.from_user.id

        if user_id not in config.ADMIN_IDS:
            return

        step = STATE[chat_id].get("step")

        if step == "AWAIT_TITLE":
            STATE[chat_id]["title"] = message.text.strip()
            STATE[chat_id]["step"] = "AWAIT_THUMB"
            bot.send_message(chat_id, "✅ টাইটেল পাওয়া গেছে!\n\nএখন ভিডিওর **পোস্টার/থাম্বনেইল (Photo)** পাঠান (বা স্কিপ করতে /skip লিখুন):")
            return

        if step == "AWAIT_THUMB" and message.text.lower() == "/skip":
            STATE[chat_id]["thumbnail"] = config.DEFAULT_THUMBNAIL
            STATE[chat_id]["step"] = "AWAIT_BUTTON"
            bot.send_message(chat_id, "⏩ থাম্বনেইল স্কিপ করা হয়েছে।\n\nএবার **বাটনের নাম বা পার্ট নম্বর** দিন (যেমন: Part 1, Part 2, Download):")
            return

        if step == "AWAIT_BUTTON":
            button_name = message.text.strip()
            data = STATE[chat_id]
            del STATE[chat_id]

            def save_series_worker():
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                async def do_save():
                    # ১. চেক করা এই টাইটেলের মেইন ভিডিও আছে কিনা
                    existing = await db.series.find_one({"title": data["title"]})
                    if not existing:
                        series_id = await db.series.insert_one({
                            "title": data["title"],
                            "thumbnail": data.get("thumbnail", config.DEFAULT_THUMBNAIL),
                            "views": 0
                        })
                        parent_id = series_id.inserted_id
                    else:
                        parent_id = existing["_id"]
                        # থাম্বনেইল থাকলে আপডেট করা
                        if "thumbnail" in data and data["thumbnail"] != config.DEFAULT_THUMBNAIL:
                            await db.series.update_one({"_id": parent_id}, {"$set": {"thumbnail": data["thumbnail"]}})

                    # ২. পার্ট ইনসার্ট করা
                    await db.video_parts.insert_one({
                        "series_id": parent_id,
                        "title": data["title"],
                        "file_id": data["file_id"],
                        "button_text": button_name,
                        "clicks": 0
                    })

                loop.run_until_complete(do_save())
                loop.close()

                bot.send_message(
                    chat_id,
                    f"🎉 **সফলভাবে সেভ হয়েছে!**\n\n📌 **সিরিজ:** {data['title']}\n🔘 **পার্ট/বাটন:** {button_name}\n🖼 **থাম্বনেইল:** রেডি!\n\nইউজাররা এখন মিনি অ্যাপে এই পার্টটি দেখতে পারবে।"
                )

            threading.Thread(target=save_series_worker).start()

    # ৪. ধাপ গ: থাম্বনেইল ছবি আসলে ImgBB ক্লাউডে আপলোড
    @bot.message_handler(content_types=['photo'])
    def handle_photo(message):
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
            STATE[chat_id]["step"] = "AWAIT_BUTTON"
            bot.send_message(chat_id, "✅ থাম্বনেইল ক্লাউডে সেভ হয়েছে!\n\nএবার **বাটনের নাম বা পার্ট নম্বর** দিন (যেমন: Part 1, Part 2, Download):")
