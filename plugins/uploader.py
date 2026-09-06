from telegram import Update
from telegram.ext import MessageHandler, filters, ContextTypes

STATE = {}

def setup(app, tg_app, db, config):

    async def handle_video_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        # শুধু অনুমোদিত অ্যাডমিন ভিডিও আপলোড করতে পারবে
        if user_id not in config.ADMIN_IDS:
            return

        # ধাপ ১: ভিডিও ফরওয়ার্ড বা সেন্ড করলে
        if update.message.video:
            STATE[chat_id] = {
                "step": "AWAIT_TITLE",
                "file_id": update.message.video.file_id
            }
            await update.message.reply_text(
                f"🎬 **[{config.APP_NAME}] ভিডিও শনাক্ত হয়েছে!**\n\nএখন দয়া করে **ভিডিওর টাইটেল/নাম** লিখে পাঠান:"
            )
            return

        # ধাপ ২: টাইটেল ইনপুট নিলে
        if chat_id in STATE and STATE[chat_id].get("step") == "AWAIT_TITLE":
            STATE[chat_id]["title"] = update.message.text
            STATE[chat_id]["step"] = "AWAIT_BUTTON"
            await update.message.reply_text(
                "✅ টাইটেল যুক্ত হয়েছে!\n\nএবার **বাটনের নাম বা পার্ট নম্বর** দিন (যেমন: Part 1, HD Download, কোম্পানি নাম):"
            )
            return

        # ধাপ ৩: বাটনের নাম পেলে ডেটাবেজে সেভ
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
                f"🌐 ওয়েব অ্যাডমিন প্যানেল থেকে থাম্বনেইল পরিবর্তন করতে পারবেন।"
            )

    tg_app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_video_flow))
