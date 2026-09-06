from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import MessageHandler, CommandHandler, filters, ContextTypes

STATE = {}

def setup(app, tg_app, db, config):

    # ১. ইউজার /start কমান্ড দিলে ব্যানার পোস্টার সহ আকর্ষণীয় ওয়েলকাম মেসেজ যাবে
    async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        
        # মিনি অ্যাপ ওপেন করার বাটন
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🔥 Watch Now (ভিডিও দেখুন) 🔥", 
                    web_app=WebAppInfo(url=config.WEBAPP_URL)
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            # পোস্টার ছবি সহ ক্যাপশনে টেক্সট এবং বাটন পাঠানো হচ্ছে
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=config.WELCOME_POSTER,
                caption=config.WELCOME_TEXT,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        except Exception as e:
            # কোনো কারণে ছবির লিংকে সমস্যা হলে সরাসরি টেক্সট ও বাটন পাঠাবে
            await update.message.reply_text(
                config.WELCOME_TEXT,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )

    # ২. অ্যাডমিন ভিডিও আপলোড এবং স্টেপ-বাই-স্টেপ প্রসেস
    async def handle_video_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        # শুধু অ্যাডমিন ভিডিও আপলোড করতে পারবে
        if user_id not in config.ADMIN_IDS:
            return

        # ধাপ ক: ভিডিও ফরওয়ার্ড বা আপলোড করলে
        if update.message.video:
            STATE[chat_id] = {
                "step": "AWAIT_TITLE",
                "file_id": update.message.video.file_id
            }
            await update.message.reply_text(
                f"🎬 **[{config.APP_NAME}] ভিডিও পাওয়া গেছে!**\n\nএখন দয়া করে **ভিডিওর টাইটেল/নাম** লিখে পাঠান:"
            )
            return

        # ধাপ খ: টাইটেল গ্রহণ করলে
        if chat_id in STATE and STATE[chat_id].get("step") == "AWAIT_TITLE":
            STATE[chat_id]["title"] = update.message.text
            STATE[chat_id]["step"] = "AWAIT_BUTTON"
            await update.message.reply_text(
                "✅ টাইটেল গ্রহণ করা হয়েছে!\n\nএবার **বাটনের নাম বা পার্ট নম্বর** দিন (যেমন: Part 1, Watch Video, ডাউনলোড পার্ট ১):"
            )
            return

        # ধাপ গ: বাটনের নাম পেলে MongoDB-তে সেভ
        if chat_id in STATE and STATE[chat_id].get("step") == "AWAIT_BUTTON":
            button_name = update.message.text
            file_id = STATE[chat_id]["file_id"]
            title = STATE[chat_id]["title"]

            await db.videos.insert_one({
                "file_id": file_id,
                "title": title,
                "button_text": button_name,
                "thumbnail": config.DEFAULT_THUMBNAIL
            })

            del STATE[chat_id]
            await update.message.reply_text(
                f"🎉 **{config.APP_NAME} এ সফলভাবে ভিডিও সেভ হয়েছে!**\n\n"
                f"📌 **টাইটেল:** {title}\n"
                f"🔘 **বাটন:** {button_name}\n"
                f"🌐 ওয়েব প্যানেল (/admin) থেকে যেকোনো সময় এর 16:9 থাম্বনেইল পরিবর্তন করতে পারবেন।"
            )

    # হ্যান্ডলার রেজিস্টার
    tg_app.add_handler(CommandHandler("start", start_command))
    tg_app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_video_flow))
