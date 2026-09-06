from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import MessageHandler, CommandHandler, filters, ContextTypes

STATE = {}

def setup(app, tg_app, db, config):

    # ১. ইউজার /start কমান্ড দিলে অ্যাপ ওপেন করার বাটন আসবে
    async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [
                InlineKeyboardButton(
                    text=f"🚀 Open {config.APP_NAME}", 
                    web_app=WebAppInfo(url=config.WEBAPP_URL)  # config.py থেকে লিংক টানবে
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"স্বাগতম **{config.APP_NAME}** এ!\n\nভিডিও দেখতে বা ডাউনলোড করতে নিচের বাটনে ক্লিক করুন 👇",
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
                f"🎬 **[{config.APP_NAME}] ভিডিও শনাক্ত হয়েছে!**\n\nএখন দয়া করে **ভিডিওর টাইটেল/নাম** লিখে পাঠান:"
            )
            return

        # ধাপ খ: টাইটেল গ্রহণ করলে
        if chat_id in STATE and STATE[chat_id].get("step") == "AWAIT_TITLE":
            STATE[chat_id]["title"] = update.message.text
            STATE[chat_id]["step"] = "AWAIT_BUTTON"
            await update.message.reply_text(
                "✅ টাইটেল যুক্ত হয়েছে!\n\nএবার **বাটনের নাম বা পার্ট নম্বর** দিন (যেমন: Part 1, Full Video, কোম্পানি নাম):"
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
                f"🎉 **{config.APP_NAME} এ সফলভাবে যুক্ত হয়েছে!**\n\n"
                f"📌 **টাইটেল:** {title}\n"
                f"🔘 **বাটন:** {button_name}\n"
                f"🌐 ওয়েব প্যানেল থেকে থাম্বনেইল পরিবর্তন করতে পারবেন।"
            )

    # হ্যান্ডলার যুক্ত করা
    tg_app.add_handler(CommandHandler("start", start_command))
    tg_app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_video_flow))
