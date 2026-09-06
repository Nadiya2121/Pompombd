from fastapi import Request
from bson import ObjectId

def setup(app, tg_app, db, config):

    # সব ভিডিওর তালিকা পাওয়ার API
    @app.get("/api/videos")
    async def get_videos():
        videos = await db.videos.find().to_list(length=200)
        for v in videos:
            v["_id"] = str(v["_id"])
        return videos

    # থাম্বনেইল, টাইটেল ও বাটন এডিট করার API
    @app.post("/api/admin/edit-video")
    async def edit_video(req: Request):
        data = await req.json()
        vid_id = data.get("id")
        await db.videos.update_one(
            {"_id": ObjectId(vid_id)},
            {"$set": {
                "title": data.get("title"),
                "button_text": data.get("button_text"),
                "thumbnail": data.get("thumbnail")
            }}
        )
        return {"status": "success", "message": "ভিডিও আপডেট সম্পন্ন!"}

    # আনলিমিটেড নতুন ডিরেক্ট লিংক যোগ করার API
    @app.post("/api/admin/add-link")
    async def add_link(req: Request):
        data = await req.json()
        url = data.get("url")
        if url:
            await db.direct_links.insert_one({"url": url, "clicks": 0})
            return {"status": "success", "message": "নতুন লিংক যুক্ত হয়েছে!"}
        return {"status": "error", "message": "লিংক পাওয়া যায়নি"}
