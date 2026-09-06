import time
import threading
import requests
from pymongo import MongoClient
from telebot import types
from fastapi import Request

STATE = {}
BULK_STATE = {}  # বাল্ক আপলোড ট্র্যাকিং স্টেট

def setup(app, bot, db, config):

    sync_client = MongoClient(config.MONGO_URI)
    sync_db = sync_client.get_default_database("pompom_db")

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
                    return data["data"].get("medium", {}).get("url") or data["data"]["url"]
        except Exception:
            pass
        return config.DEFAULT_THUMBNAIL

    def get_next_series_code():
        last = sync_db.series.find_one(sort=[("code", -1)])
        if last and "code" in last:
            return last["code"] + 1
        return 101

    def get_settings():
        settings = sync_db.settings.find_one({"type": "global"})
        if not settings:
            return {"protect_content": True, "auto_delete_minutes": 10}
        return {
            "protect_content": settings.get("protect_content", True),
            "auto_delete_minutes": settings.get("auto_delete_minutes", 10)
        }

    def schedule_auto_delete(chat_id, message_id, minutes):
        if minutes <= 0:
            return

        def delete_task():
            time.sleep(minutes * 60)
            try:
                bot.delete_message(chat_id=chat_id, message_id=message_id)
                notice = bot.send_message(
                    chat_id, 
                    "⚠️ **সময় শেষ! পূর্বের ভিডিও ফাইলটি স্বয়ংক্রিয়ভাবে মুছে ফেলা হয়েছে।**\nআবার দেখতে চাইলে মিনি অ্যাপ থেকে আনলক করুন।"
                )
                time.sleep(60)
                bot.delete_message(chat_id=chat_id, message_id=notice.message_id)
            except Exception:
                pass

        threading.Thread(target=delete_task, daemon=True).start()

    # =========================================================================
    # ১. ডিরেক্ট ভিডিও ডেলিভারি API
    # =========================================================================
    @app.post("/api/deliver-video")
    async def deliver_video_api(req: Request):
        data = await req.json()
        part_id = data.get("part_id")
        user_id = data.get("user_id")

        if not part_id or not user_id:
            return {"status": "error", "message": "Missing params"}

        def send_file_task():
            try:
                from bson import ObjectId
                part = sync_db.video_parts.find_one({"_id": ObjectId(part_id)})
                if part:
                    cfg = get_settings()
                    del_min = cfg["auto_delete_minutes"]
                    timer_text = f"\n\n⏳ **এই ভিডিওটি {del_min} মিনিট পর স্বয়ংক্রিয়ভাবে মুছে যাবে!**" if del_min > 0 else ""

                    sent_msg = bot.send_video(
                        chat_id=int(user_id),
                        video=part["file_id"],
                        protect_content=cfg["protect_content"],
                        caption=(
                            f"🎉 **আপনার আনলক করা ভিডিও:**\n\n"
                            f"📌 **সিরিজ:** {part.get('series_title', 'Video')}\n"
                            f"🔘 **পার্ট:** {part['button_text']}"
                            f"{timer_text}\n\nআমাদের সাথে থাকার জন্য ধন্যবাদ! ❤️"
                        )
                    )

                    if del_min > 0:
                        schedule_auto_delete(int(user_id), sent_msg.message_id, del_min)

            except Exception as e:
                print(f"Direct Delivery Error: {e}")

        threading.Thread(target=send_file_task).start()
        return {"status": "success"}

    # =========================================================================
    # ২. টেলিগ্রাম বট /start হ্যান্ডলার
    # =========================================================================
    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        chat_id = message.chat.id
        text = message.text or ""

        if len(text.split()) > 1 and text.split()[1].startswith("get_"):
            part_id = text.split()[1].replace("get_", "")
            try:
                from bson import ObjectId
                part = sync_db.video_parts.find_one({"_id": ObjectId(part_id)})
                if part:
                    cfg = get_settings()
                    del_min = cfg["auto_delete_minutes"]
                    timer_text = f"\n\n⏳ **এই ভিডিওটি {del_min} মিনিট পর স্বয়ংক্রিয়ভাবে মুছে যাবে!**" if del_min > 0 else ""

                    sent_msg = bot.send_video(
                        chat_id=chat_id,
                        video=part["file_id"],
                        protect_content=cfg["protect_content"],
                        caption=(
                            f"🎉 **আপনার আনলক করা ভিডিও:**\n\n"
                            f"📌 **সিরিজ:** {part.get('series_title', 'Video')}\n"
                            f"🔘 **পার্ট:** {part['button_text']}"
                            f"{timer_text}\n\nআমাদের সাথে থাকার জন্য ধন্যবাদ! ❤️"
                        )
                    )
                    if del_min > 0:
                        schedule_auto_delete(chat_id, sent_msg.message_id, del_min)
                    return
            except Exception:
                pass

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

    # =========================================================================
    # ৩. 🌟 বাল্ক আপলোড মোড (/addparts) - একসাথে অনেকগুলো পার্ট অ্যাড করা
    # =========================================================================
    @bot.message_handler(commands=['addparts'])
    def handle_bulk_command(message):
        user_id = message.from_user.id
        chat_id = message.chat.id

        if user_id not in config.ADMIN_IDS:
            return

        BULK_STATE[chat_id] = {"step": "AWAIT_BULK_CODE"}
        bot.send_message(
            chat_id,
            "⚡ **একসাথে অনেকগুলো পার্ট যোগ করার মোড চালু হয়েছে!**\n\n"
            "যে ভিডিওতে পার্টগুলো যোগ করতে চান, সেই ভিডিওর **কোড নম্বর** দিন (যেমন: 101, 102):"
        )

    # বাল্ক আপলোড শেষ করার কমান্ড (/done)
    @bot.message_handler(commands=['done'])
    def handle_bulk_done(message):
        chat_id = message.chat.id
        if chat_id in BULK_STATE:
            count = BULK_STATE[chat_id].get("uploaded_count", 0)
            title = BULK_STATE[chat_id].get("series_title", "Video")
            del BULK_STATE[chat_id]
            bot.send_message(
                chat_id,
                f"🎉 **বাল্ক আপলোড সম্পন্ন হয়েছে!**\n\n"
                f"📌 **ভিডিও:** {title}\n"
                f"🔢 **মোট নতুন পার্ট যুক্ত হয়েছে:** {count} টি\n\n"
                f"🌐 মিনি অ্যাপ ও অ্যাডমিন প্যানেল চেক করুন!"
            )
        else:
            bot.send_message(chat_id, "❌ আপনি কোনো বাল্ক আপলোড মোডে নেই!")

    # =========================================================================
    # ৪. ভিডিও আপলোড হ্যান্ডলার (সিঙ্গেল এবং বাল্ক মোড একসাথে)
    # =========================================================================
    @bot.message_handler(content_types=['video'])
    def handle_video(message):
        user_id = message.from_user.id
        chat_id = message.chat.id

        if user_id not in config.ADMIN_IDS:
            return

        # প্রাইভেট DB চ্যানেলে ব্যাকআপ
        try:
            backup_msg = bot.forward_message(config.DB_CHANNEL_ID, chat_id, message.message_id)
            saved_file_id = backup_msg.video.file_id
        except Exception:
            saved_file_id = message.video.file_id

        # ক) যদি বাল্ক মোড চালু থাকে (একসাথে অনেকগুলো ভিডিও ফরওয়ার্ড করলে)
        if chat_id in BULK_STATE and BULK_STATE[chat_id].get("step") == "RECEIVING_VIDEOS":
            parent_id = BULK_STATE[chat_id]["parent_id"]
            series_title = BULK_STATE[chat_id]["series_title"]

            # বর্তমানে এই সিরিজের মোট কয়টি পার্ট আছে বের করা
            current_parts_count = sync_db.video_parts.count_documents({"series_id": parent_id})
            next_part_num = current_parts_count + 1
            button_name = f"🎬 Video Part {next_part_num}"

            # পার্ট সেভ
            sync_db.video_parts.insert_one({
                "series_id": parent_id,
                "series_title": series_title,
                "file_id": saved_file_id,
                "button_text": button_name,
                "clicks": 0
            })

            BULK_STATE[chat_id]["uploaded_count"] = BULK_STATE[chat_id].get("uploaded_count", 0) + 1
            bot.send_message(chat_id, f"✅ সেভ হয়েছে: **{button_name}**")
            return

        # খ) সাধারণ সিঙ্গেল ভিডিও আপলোড
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
    # ৫. টেক্সট হ্যান্ডলার
    # =========================================================================
    @bot.message_handler(func=lambda msg: (msg.chat.id in STATE or msg.chat.id in BULK_STATE) and msg.text)
    def handle_admin_inputs(message):
        chat_id = message.chat.id
        user_id = message.from_user.id

        if user_id not in config.ADMIN_IDS:
            return

        text = message.text.strip()

        # বাল্ক মোডের জন্য কোড নেওয়া
        if chat_id in BULK_STATE and BULK_STATE[chat_id].get("step") == "AWAIT_BULK_CODE":
            if not text.isdigit():
                bot.send_message(chat_id, "❌ শুধুমাত্র সংখ্যায় কোড দিন (যেমন: 101):")
                return
            code = int(text)
            series = sync_db.series.find_one({"code": code})
            if not series:
                bot.send_message(chat_id, f"❌ কোড #{code} এর ভিডিও পাওয়া যায়নি! আবার দিন:")
                return

            BULK_STATE[chat_id]["parent_id"] = series["_id"]
            BULK_STATE[chat_id]["series_title"] = series["title"]
            BULK_STATE[chat_id]["step"] = "RECEIVING_VIDEOS"
            BULK_STATE[chat_id]["uploaded_count"] = 0

            bot.send_message(
                chat_id,
                f"✅ **ভিডিও নিশ্চিত হয়েছে:** {series['title']}\n\n"
                f"🚀 **এখন যতগুলো ভিডিও ইচ্ছা একসাথে সিলেক্ট করে ফরওয়ার্ড (Forward) করে দিন!**\n"
                f"বট স্বয়ংক্রিয়ভাবে একটার পর একটা পার্ট হিসেবে সেভ করে নেবে।\n\n"
                f"সবগুলো পাঠানো শেষ হলে নিচে **`/done`** লিখে সেন্ড করবেন।"
            )
            return

        # সাধারণ আপলোডের স্টেপ
        if chat_id in STATE:
            step = STATE[chat_id].get("step")

            if step == "CHOOSE_TYPE":
                if "নতুন" in text:
                    STATE[chat_id]["is_new"] = True
                    STATE[chat_id]["step"] = "AWAIT_TITLE"
                    bot.send_message(chat_id, "📝 এখন **ভিডিওর একটি সুন্দর টাইটেল/নাম** লিখে পাঠান:", reply_markup=types.ReplyKeyboardRemove())
                elif "আগের" in text:
                    STATE[chat_id]["is_new"] = False
                    STATE[chat_id]["step"] = "AWAIT_CODE"
                    bot.send_message(chat_id, "🔢 আগের ভিডিওটির **ইউনিক কোড** নম্বরটি দিন (যেমন: 101, 102):", reply_markup=types.ReplyKeyboardRemove())
                return

            if step == "AWAIT_CODE":
                if not text.isdigit():
                    bot.send_message(chat_id, "❌ শুধুমাত্র সংখ্যায় কোড দিন (যেমন: 101):")
                    return
                code = int(text)
                series = sync_db.series.find_one({"code": code})
                if not series:
                    bot.send_message(chat_id, f"❌ কোড #{code} এর ভিডিও পাওয়া যায়নি! আবার দিন:")
                    return
                
                STATE[chat_id]["parent_id"] = series["_id"]
                STATE[chat_id]["series_title"] = series["title"]
                STATE[chat_id]["step"] = "AWAIT_PART_NUM"
                bot.send_message(chat_id, f"✅ ভিডিও পাওয়া গেছে: **{series['title']}**\n\nএখন শুধু **পার্ট নম্বর** লিখে পাঠান (যেমন: 2 বা 3):")
                return

            if step == "AWAIT_TITLE":
                STATE[chat_id]["title"] = text
                STATE[chat_id]["step"] = "AWAIT_THUMB"
                bot.send_message(chat_id, "✅ টাইটেল সেট হয়েছে!\n\nএখন ভিডিওর **পোস্টার/থাম্বনেইল (Photo)** পাঠান (না থাকলে /skip লিখুন):")
                return

            if step == "AWAIT_THUMB" and text.lower() == "/skip":
                STATE[chat_id]["thumbnail"] = config.DEFAULT_THUMBNAIL
                STATE[chat_id]["step"] = "AWAIT_PART_NUM"
                bot.send_message(chat_id, "⏩ থাম্বনেইল স্কিপ হয়েছে।\n\nএখন শুধু **পার্ট নম্বর** লিখে দিন (যেমন: শুধু 1 লিখলেই হবে):")
                return

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
                        f"🌐 ভিডিওটি এখন মিনি অ্যাপ ও অ্যাডমিন প্যানেলে লাইভ!"
                    )
                except Exception as e:
                    bot.send_message(chat_id, f"❌ সেভ করতে ত্রুটি: {str(e)}")

    # ৬. থাম্বনেইল হ্যান্ডলার
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

            bot.send_message(chat_id, "⏳ থাম্বনেইল ক্লাউডে অপ্টিমাইজ ও আপলোড হচ্ছে...")
            cdn_url = upload_to_imgbb(temp_path)

            STATE[chat_id]["thumbnail"] = cdn_url
            STATE[chat_id]["step"] = "AWAIT_PART_NUM"
            bot.send_message(chat_id, "✅ থাম্বনেইল ক্লাউডে সেভ হয়েছে!\n\nএবার শুধু **পার্ট নম্বর** লিখে পাঠান (যেমন: 1):")
