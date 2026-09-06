import threading
from telebot import types

STATE = {}

def setup(app, bot, db, config):

    # ১. /start দিলে ওয়েলকাম পোস্টার ও মিনি অ্যাপ বাটন
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
            bot.send_message(
                chat_id=chat_id,
                text=config.WELCOME_TEXT,
                reply_markup=markup
            )

    # ২. অ্যাডমিন ভিডিও পাঠালে ডিটেক্ট করা
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
        bot.send_message(
            chat_id, 
            f"🎬 **[{config.APP_NAME}] ভিডিও পাওয়া গেছে!**\n\nএখন **ভিডিওর টাইটেল/নাম** লিখে পাঠান:"
        )

    # ৩. টাইটেল এবং বাটন টেক্সট হ্যান্ডলার
    @bot.message_handler(func=lambda msg: msg.chat.id in STATE and msg.text)
    def handle_steps(message):
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
            STATE[chat_id]["title"] = message.text
            STATE[chat_id]["step"] = "AWAIT_BUTTON"
            bot.send_message(
                chat_id, 
                "✅ টাইটেল গ্রহণ করা হয়েছে!\n\nএবার **বাটনের নাম বা পার্ট নম্বর** দিন (যেমন: Part 1, Watch Video):"
            )
            return

        # ধাপ খ: বাটন নাম পেলে ডাটাবেজে সেভ করা (Non-blocking Thread)
        if step == "AWAIT_BUTTON":
            button_name = message.text
            file_id = current_data["file_id"]
            title = current_data["title"]

            # স্টেট থেকে ডিলিট করে দেওয়া যাতে রিপিটেড মেসেজ সমস্যা না করে
            del STATE[chat_id]

            # ব্যাকগ্রাউন্ড থ্রেডে সেভ হবে যাতে বট না আটকায়
            def save_worker():
                try:
                    # Motor দিয়ে ব্যাকগ্রাউন্ডে ইনসার্ট
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    async def do_insert():
                        await db.videos.insert_one({
                            "file_id": file_id,
                            "title": title,
                            "button_text": button_name,
                            "thumbnail": config.DEFAULT_THUMBNAIL
                        })
                    
                    loop.run_until_complete(do_insert())
                    loop.close()

                    # সফলভাবে সেভ হলে ইউজারকে নিশ্চিত করা
                    bot.send_message(
                        chat_id,
                        f"🎉 **সফলভাবে সেভ হয়েছে!**\n\n"
                        f"📌 **টাইটেল:** {title}\n"
                        f"🔘 **বাটন:** {button_name}\n\n"
                        f"🌐 মিনি অ্যাপ ও অ্যাডমিন প্যানেল চেক করুন, ভিডিওটি যুক্ত হয়ে গেছে!"
                    )
                except Exception as e:
                    bot.send_message(chat_id, f"❌ সেভ করতে ত্রুটি হয়েছে: {str(e)}")

            threading.Thread(target=save_worker).start()
