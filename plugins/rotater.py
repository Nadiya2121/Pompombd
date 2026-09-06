import random
from bson import ObjectId
from fastapi import Request

def setup(app, bot, db, config):

    # ১. মিনি অ্যাপের জন্য ভিডিও ও পার্টস লোড
    @app.get("/api/videos-with-parts")
    async def get_series_and_parts():
        series_list = await db.series.find().sort("_id", -1).to_list(100)
        result = []
        for s in series_list:
            parts = await db.video_parts.find({"series_id": s["_id"]}).to_list(50)
            parts_clean = [{"id": str(p["_id"]), "button_text": p["button_text"], "clicks": p.get("clicks", 0)} for p in parts]
            result.append({
                "id": str(s["_id"]),
                "title": s["title"],
                "thumbnail": s["thumbnail"],
                "parts": parts_clean
            })
        return result

    # ২. স্মার্ট অ্যাড গেট ও আসল বটের ইউজারনেম পাস করা
    @app.get("/api/get-ad-gate")
    async def get_ad_gate():
        settings = await db.settings.find_one({"type": "global"})
        wait_seconds = settings.get("wait_seconds", 7) if settings else 7

        # বটের আসল ইউজারনেম লাইভ আনা
        try:
            bot_info = bot.get_me()
            bot_username = bot_info.username
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
            "bot_username": bot_username  # বটের আসল ইউজারনেম স্বয়ংক্রিয়ভাবে যাবে
        }

    # ৩. অ্যাডমিন প্যানেল থেকে টাইমার আপডেট
    @app.post("/api/admin/set-timer")
    async def set_timer(req: Request):
        data = await req.json()
        seconds = int(data.get("seconds", 7))
        await db.settings.update_one(
            {"type": "global"},
            {"$set": {"wait_seconds": seconds}},
            upsert=True
        )
        return {"status": "success"}
