import threading
import requests
from telebot import types

STATE = {}

def setup(app, bot, db, config):

    # ImgBB তে ছবি আপলোড করার অটোমেটিক হেল্পার ফাংশন
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
        except Exception as e:
            print(f"ImgBB Upload Error: {e}")
        return config.DEFAULT_THUMBNAIL

    # ১. /start কমান্ড
    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        chat_id = message.chat.id
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
            bot.send_message(chat_id, config.WELCOME_TEXT, reply_markup=markup)

    # ২. ভিডিও আপলোড ডিটেক্ট করা
    @bot.message_handler(content_types=['video'])
    def handle_video(message):
        user_id = message.from_user.id
        chat_id = message.chat.id

        if user_id not in config.ADMIN_IDS:
            return

        # DB চ্যানেলে অটোমেটিক ব্যাকআপ ফরওয়ার্ড
        try:
            backup_msg = bot.forward_message(
                chat_id=config.DB_CHANNEL_ID,
                from_chat_id=chat_id,
                message_id=message.message_id
            )
            saved_file_id = backup_msg.video.file_id
            channel_msg_id = backup_msg.message_id
        except Exception as e:
            print(f"DB Channel Forward Error: {e}")
            saved_file_id = message.video.file_id
            channel_msg_id = None

        STATE[chat_id] = {
            "step": "AWAIT_THUMB",
            "file_id": saved_file_id,
            "db_channel_msg_id": channel_msg_id
        }
        bot.send_message(
            chat_id, 
            f"🎬 **ভিডিও DB চ্যানেলে সুরক্ষিতভাবে ব্যাকআপ হয়েছে!**\n\nএবার ভিডিওর **পোস্টার/থাম্বনেইল (Photo)** সেন্ড করুন (না থাকলে /skip লিখুন):"
        )

    # ৩. থাম্বনেইল ছবি হ্যান্ডলার
    @bot.message_handler(content_types=['photo'])
    def handle_photo(message):
        chat_id = message.chat.id
        user_id = message.from_user.id

        if user_id not in config.ADMIN_IDS or chat_id not in STATE:
            return

        if STATE[chat_id].get("step") == "AWAIT_THUMB":
            # সবচেয়ে বড় রেজোলিউশনের ছবি ডাউনলোড
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded = bot.download_file(file_info.file_path)
            
            temp_path = f"thumb_{chat_id}.jpg"
            with open(temp_path, 'wb') as f:
                f.write(downloaded)

            # DB চ্যানেলে ছবি ব্যাকআপ পাঠানো
            try:
                bot.send_photo(config.DB_CHANNEL_ID, photo=message.photo[-1].file_id, caption="📸 Poster Backup")
            except Exception:
                pass

            # ImgBB ক্লাউড CDN এ আপলোড
            bot.send_message(chat_id, "⏳ থাম্বনেইল ImgBB ক্লাউডে আপলোড হচ্ছে...")
            cdn_url = upload_to_imgbb(temp_path)

            STATE[chat_id]["thumbnail"] = cdn_url
            STATE[chat_id]["step"] = "AWAIT_TITLE"
            bot.send_message(chat_id, "✅ থাম্বনেইল ক্লাউডে সেভ হয়েছে!\n\nএখন **ভিডিওর টাইটেল/নাম** লিখে পাঠান:")

    # ৪. টেক্সট হ্যান্ডলার (স্কিপ, টাইটেল, বাটন)
    @bot.message_handler(func=lambda msg: msg.chat.id in STATE and msg.text)
    def handle_steps(message):
        chat_id = message.chat.id
        user_id = message.from_user.id

        if user_id not in config.ADMIN_IDS:
            return

        current_data = STATE.get(chat_id)
        step = current_data.get("step")

        # থাম্বনেইল স্কিপ করলে
        if step == "AWAIT_THUMB" and message.text.lower() == "/skip":
            STATE[chat_id]["thumbnail"] = config.DEFAULT_THUMBNAIL
            STATE[chat_id]["step"] = "AWAIT_TITLE"
            bot.send_message(chat_id, "⏩ থাম্বনেইল স্কিপ করা হয়েছে।\n\nএখন **ভিডিওর টাইটেল/নাম** লিখে পাঠান:")
            return

        # টাইটেল পাওয়ার পর
        if step == "AWAIT_TITLE":
            STATE[chat_id]["title"] = message.text
            STATE[chat_id]["step"] = "AWAIT_BUTTON"
            bot.send_message(chat_id, "✅ টাইটেল যুক্ত হয়েছে!\n\nএবার **বাটনের নাম বা পার্ট নম্বর** দিন (যেমন: Part 1, Watch Full Video):")
            return

        # বাটন পাওয়ার পর ডাটাবেজে পার্মানেন্ট সেভ
        if step == "AWAIT_BUTTON":
            button_name = message.text
            file_id = current_data["file_id"]
            title = current_data["title"]
            thumbnail = current_data.get("thumbnail", config.DEFAULT_THUMBNAIL)
            channel_msg_id = current_data.get("db_channel_msg_id")

            del STATE[chat_id]

            def save_worker():
                try:
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    async def do_insert():
                        await db.videos.insert_one({
                            "file_id": file_id,
                            "title": title,
                            "button_text": button_name,
                            "thumbnail": thumbnail,
                            "db_channel_msg_id": channel_msg_id,
                            "clicks": 0
                        })
                    
                    loop.run_until_complete(do_insert())
                    loop.close()

                    bot.send_message(
                        chat_id,
                        f"🎉 **{config.APP_NAME} এ সফলভাবে ভিডিও পাবলিশ হয়েছে!**\n\n"
                        f"📌 **টাইটেল:** {title}\n"
                        f"🔘 **বাটন:** {button_name}\n"
                        f"🖼 **ImgBB CDN:** {thumbnail}\n"
                        f"🔒 **DB Backup:** চ্যানেল মেসেজ আইডি #{channel_msg_id}\n\n"
                        f"🌐 ভিডিওটি এখন মিনি অ্যাপ এবং অ্যাডমিন প্যানেলে লাইভ!"
                    )
                except Exception as e:
                    bot.send_message(chat_id, f"❌ সেভ করতে ত্রুটি: {str(e)}")

            threading.Thread(target=save_worker).start()
