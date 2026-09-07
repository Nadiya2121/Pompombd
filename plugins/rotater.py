import random
from bson import ObjectId
from fastapi import Request

def setup(app, bot, db, config):

    # ১. ভিডিও ও পার্টস লোড
    @app.get("/api/videos-with-parts")
    async def get_series_and_parts():
        series_list = await db.series.find().sort("_id", -1).to_list(100)
        result = []
        for s in series_list:
            parts = await db.video_parts.find({"series_id": s["_id"]}).to_list(50)
            parts_clean = [{"id": str(p["_id"]), "button_text": p["button_text"], "clicks": p.get("clicks", 0)} for p in parts]
            result.append({
                "id": str(s["_id"]),
                "code": s.get("code", 101),
                "title": s["title"],
                "thumbnail": s["thumbnail"],
                "parts": parts_clean
            })
        return result

    # ২. অ্যাড গেট ও বট ইউজারনেম
    @app.get("/api/get-ad-gate")
    async def get_ad_gate():
        settings = await db.settings.find_one({"type": "global"})
        wait_seconds = settings.get("wait_seconds", 7) if settings else 7

        try:
            bot_username = bot.get_me().username
        except Exception:
            bot_username = ""

        links = await db.direct_links.find().to_list(100)
        ad_url = "https://google.com"

        if links:
            links.sort(key=lambda x: x.get("clicks", 0))
            selected = links[0]
            await db.direct_links.update_one({"_id": selected["_id"]}, {"$inc": {"clicks": 1}})
            ad_url = selected["url"]
        
        return {
            "url": ad_url,
            "wait_seconds": wait_seconds,
            "bot_username": bot_username
        }

    # ৩. ইউজার প্রোফাইল ও সেটিংস ইনফো
    @app.get("/api/user/info/{user_id}")
    async def get_user_info(user_id: int):
        user = await db.users.find_one({"user_id": user_id})
        settings = await db.settings.find_one({"type": "global"})
        
        return {
            "coins": user.get("coins", 0) if user else 0,
            "bkash_number": settings.get("bkash_number", "01XXXXXXXXX") if settings else "01XXXXXXXXX",
            "support_username": settings.get("support_username", "YourSupportUsername") if settings else "YourSupportUsername",
            "channel_url": settings.get("channel_url", "https://t.me/") if settings else "https://t.me/"
        }

    # ৪. কুপন রিডিম API
    @app.post("/api/coupon/redeem")
    async def redeem_coupon_api(req: Request):
        data = await req.json()
        code = data.get("code", "").strip().upper()
        user_id = int(data.get("user_id", 0))

        coupon = await db.coupons.find_one({"code": code, "active": True})
        if not coupon:
            return {"success": False, "message": "অবৈধ বা মেয়াদোত্তীর্ণ কুপন কোড!"}

        # ইউজার কি ইতিমধ্যে ব্যবহার করেছে?
        if user_id in coupon.get("used_by", []):
            return {"success": False, "message": "আপনি ইতিমধ্যে এই কুপনটি ব্যবহার করেছেন!"}

        # কয়েন যোগ করা
        coins_to_add = coupon.get("coins", 50)
        await db.users.update_one(
            {"user_id": user_id},
            {"$inc": {"coins": coins_to_add}},
            upsert=True
        )

        # কুপনে ইউজার রেকর্ড করা
        await db.coupons.update_one(
            {"_id": coupon["_id"]},
            {"$push": {"used_by": user_id}}
        )

        return {"success": True, "coins": coins_to_add}

    # ৫. কয়েন দিয়ে সরাসরি আনলক API (২০ কয়েন কাটবে)
    @app.post("/api/unlock-by-coins")
    async def unlock_by_coins_api(req: Request):
        data = await req.json()
        user_id = int(data.get("user_id", 0))
        part_id = data.get("part_id")

        user = await db.users.find_one({"user_id": user_id})
        current_coins = user.get("coins", 0) if user else 0

        if current_coins < 20:
            return {"success": False, "message": "Not enough coins"}

        # ২০ কয়েন কাটা
        await db.users.update_one({"user_id": user_id}, {"$inc": {"coins": -20}})

        # সরাসরি ভিডিও ইনবক্সে ডেলিভারি
        part = await db.video_parts.find_one({"_id": ObjectId(part_id)})
        if part:
            bot.send_video(
                chat_id=user_id,
                video=part["file_id"],
                caption=f"🎉 **২০ Coins দিয়ে আনলককৃত ভিডিও:**\n\n📌 {part.get('series_title', 'Video')} ({part['button_text']})\n\nউপভোগ করুন! ❤️"
            )

        return {"success": True}
