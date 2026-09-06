import random
from bson import ObjectId
from fastapi import Request

def setup(app, bot, db, config):

    # মিনি অ্যাপের জন্য সিরিজ ও সব পার্ট একসাথে লোড করা
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

    # স্মার্ট অ্যাড লিংক এবং অ্যাডমিন টাইমার ডিউরেশন
    @app.get("/api/get-ad-gate")
    async def get_ad_gate():
        settings = await db.settings.find_one({"type": "global"})
        wait_seconds = settings.get("wait_seconds", 7) if settings else 7

        links = await db.direct_links.find().to_list(100)
        if not links:
            return {"url": "https://google.com", "wait_seconds": wait_seconds}

        links.sort(key=lambda x: x.get("clicks", 0))
        selected = links[0]
        await db.direct_links.update_one({"_id": selected["_id"]}, {"$inc": {"clicks": 1}})
        
        return {"url": selected["url"], "wait_seconds": wait_seconds}

    # অ্যাডমিন প্যানেল থেকে টাইমার সেকেন্ড আপডেট করার API
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
