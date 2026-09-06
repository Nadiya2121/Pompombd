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

    # ১. /start কমান্ড হ্যান্ডলার
    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        chat_id = message.chat.id
        text = message.text or ""

        # যদি ইউজার আনলক শেষে ভিডিও ফাইল নিতে আসে (যেমন: /start get_ID)
        if len(text.split()) > 1 and text.split()[1].startswith("get_"):
            video_part_id = text.split()[1].replace("get_", "")
            
            def deliver_file():
                import asyncio
                from bson import ObjectId
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                async def deliver():
                    part = await db.video_parts.find_one({"_id": ObjectId(video_part_id)})
                    if part:
                        bot.send_video(
                            chat_id=chat_id,
                            video=part["file_id"],
                            caption=f"🎉 **আপনার আনলক করা ভিডিও:**\n\n📌 {part['title']} ({part['button_text']})\n\nধন্যবাদ! ❤️"
                        )
                    else:
                        bot.send_message(chat_id, "❌ দুঃখিত, ভিডিওটি ডাটাবেজে পাওয়া যায়নি!")
                loop.run_until_complete(deliver())
                loop.close()

            threading.Thread(target=deliver_file).start()
            return

        # সাধারণ /start হলে ওয়েলকাম ব্যানার এবং ওপেন অ্যাপ বাটন
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

    # ২. অ্যাডমিন ভিডিও ফরওয়ার্ড বা আপলোড করলে
    @bot.message_handler(content_types=['video'])
    def handle_video(message):
        user_id = message.from_user.id
        chat_id = message.chat.id

        # অ্যাডমিন আইডি ভ্যালিডেশন
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
        bot.send_message(
            chat_id, 
            f"🎬 **[{config.APP_NAME}] ভিডিও পাওয়া গেছে!**\n\nএখন দয়া করে **ভিডিওর টাইটেল/নাম** লিখে পাঠান:"
        )

    # ৩. টেক্সট হ্যান্ডলার (টাইটেল এবং বাটন নেম নেওয়ার জন্য)
    @bot.message_handler(func=lambda msg: msg.chat.id in STATE and msg.text)
    def handle_text_steps(message):
        chat_id = message.chat.id
        user_id = message.from_user.id

        if user_id not in config.ADMIN_IDS:
            return

        current_data = STATE.get(chat_id)
        if not current_data:
            return

        step = current_data.get("step")

        # ধাপ ক: টাইটেল গ্রহণ করা
        if step == "AWAIT_TITLE":
            STATE[chat_id]["title"] = message.text.strip()
            STATE[chat_id]["step"] = "AWAIT_THUMB"
            bot.send_message(
                chat_id, 
                "✅ টাইটেল গ্রহণ করা হয়েছে!\n\nএখন ভিডিওর **পোস্টার/থাম্বনেইল (Photo)** পাঠান (না থাকলে /skip লিখুন):"
            )
            return

        # ধাপ খ: থাম্বনেইল স্কিপ করলে
        if step == "AWAIT_THUMB" and message.text.lower() == "/skip":
            STATE[chat_id]["thumbnail"] = config.DEFAULT_THUMBNAIL
            STATE[chat_id]["step"] = "AWAIT_BUTTON"
            bot.send_message(
                chat_id, 
                "⏩ থাম্বনেইল স্কিপ হয়েছে।\n\nএবার **বাটনের নাম বা পার্ট নম্বর** দিন (যেমন: Part 1, Watch Video):"
            )
            return

        # ধাপ গ: বাটনের নাম পেলে পার্মানেন্ট সেভ
        if step == "AWAIT_BUTTON":
            button_name = message.text.strip()
            data = STATE[chat_id]
            del STATE[chat_id]

            def save_series_task():
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                async def do_save():
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
                        if "thumbnail" in data and data["thumbnail"] != config.DEFAULT_THUMBNAIL:
                            await db.series.update_one({"_id": parent_id}, {"$set": {"thumbnail": data["thumbnail"]}})

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
                    f"🎉 **সফলভাবে সেভ হয়েছে!**\n\n📌 **সিরিজ:** {data['title']}\n🔘 **পার্ট/বাটন:** {button_name}\n\n🌐 মিনি অ্যাপ চেক করুন, ভিডিওটি যুক্ত হয়ে গেছে!"
                )

            threading.Thread(target=save_series_task).start()

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
            STATE[chat_id]["step"] = "AWAIT_BUTTON"
            bot.send_message(
                chat_id, 
                "✅ থাম্বনেইল ক্লাউডে সেভ হয়েছে!\n\nএবার **বাটনের নাম বা পার্ট নম্বর** দিন (যেমন: Part 1, Part 2, Download):"
            )
