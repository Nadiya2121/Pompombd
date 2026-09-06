import asyncio
from telebot import types

STATE = {}

def setup(app, bot, db, config):

    # ১. /start দিলে ওয়েলকাম পোস্টার, টেক্সট এবং মিনি অ্যাপ বাটন
    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        chat_id = message.chat.id
        markup = types.InlineKeyboardMarkup()
        
        # মিনি অ্যাপ ওপেন বাটন
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

    # ২. অ্যাডমিন ভিডিও আপলোড ফ্লো
    @bot.message_handler(content_types=['video'])
    def handle_video(message):
        user_id = message.from_user.id
        chat_id = message.chat.id

        if user_id not in config.ADMIN_IDS:
            return

        STATE[chat_id] = {
            "step": "AWAIT_TITLE",
            "file_id": message.video.file_id
        }
        bot.send_message(chat_id, f"🎬 **[{config.APP_NAME}] ভিডিও পাওয়া গেছে!**\n\nএখন **ভিডিওর টাইটেল/নাম** লিখে পাঠান:")

    # ৩. টেক্সট হ্যান্ডলার (টাইটেল এবং বাটন নেম সেভ)
    @bot.message_handler(func=lambda msg: msg.chat.id in STATE and msg.text)
    def handle_steps(message):
        chat_id = message.chat.id
        user_id = message.from_user.id

        if user_id not in config.ADMIN_IDS:
            return

        current_step = STATE[chat_id].get("step")

        # টাইটেল পাওয়ার পর
        if current_step == "AWAIT_TITLE":
            STATE[chat_id]["title"] = message.text
            STATE[chat_id]["step"] = "AWAIT_BUTTON"
            bot.send_message(chat_id, "✅ টাইটেল গ্রহণ করা হয়েছে!\n\nএবার **বাটনের নাম বা পার্ট নম্বর** দিন (যেমন: Part 1, Watch Video):")
            return

        # বাটন পাওয়ার পর ডাটাবেজে সেভ
        if current_step == "AWAIT_BUTTON":
            button_name = message.text
            file_id = STATE[chat_id]["file_id"]
            title = STATE[chat_id]["title"]

            # মঙ্গোডিবিতে সেভ
            async def save_to_db():
                await db.videos.insert_one({
                    "file_id": file_id,
                    "title": title,
                    "button_text": button_name,
                    "thumbnail": config.DEFAULT_THUMBNAIL
                })
            
            asyncio.run(save_to_db())
            del STATE[chat_id]

            bot.send_message(
                chat_id,
                f"🎉 **{config.APP_NAME} এ সফলভাবে সেভ হয়েছে!**\n\n"
                f"📌 **টাইটেল:** {title}\n"
                f"🔘 **বাটন:** {button_name}\n"
                f"🌐 ওয়েব প্যানেল (/admin) থেকে 16:9 থাম্বনেইল পরিবর্তন করতে পারবেন।"
            )
