from fastapi import Request
from bson import ObjectId

def setup(app, bot, db, config):

    # ইউজার ট্র্যাকিং API
    @app.get("/api/user/track-visit")
    async def track_user():
        await db.analytics.update_one(
            {"type": "traffic"},
            {"$inc": {"active_users": 1}},
            upsert=True
        )
        return {"status": "ok"}

    # ভিডিও ক্লিক ট্র্যাকিং API
    @app.post("/api/video/track-click/{vid_id}")
    async def track_video_click(vid_id: str):
        try:
            await db.videos.update_one(
                {"_id": ObjectId(vid_id)},
                {"$inc": {"clicks": 1}}
            )
        except Exception:
            pass
        return {"status": "ok"}

    # স্মার্ট ডিরেক্ট লিংক রোটেশন API
    @app.get("/api/get-ad-link")
    async def get_ad_link():
        links = await db.direct_links.find({}).to_list(length=200)
        
        if not links:
            return {"url": "https://google.com"}

        # স্মার্ট অ্যালগরিদম: সবচেয়ে কম ক্লিক পড়া লিংকটি ইউজার আগে পাবে (Round-Robin)
        links.sort(key=lambda x: x.get("clicks", 0))
        selected = links[0]

        # ক্লিক কাউন্ট বাড়ানো
        await db.direct_links.update_one({"_id": selected["_id"]}, {"$inc": {"clicks": 1}})
        
        # ওভারঅল অ্যাড ক্লিক অ্যানালিটিক্স আপডেট
        await db.analytics.update_one(
            {"type": "traffic"},
            {"$inc": {"total_ad_clicks": 1}},
            upsert=True
        )

        return {"url": selected["url"]}
