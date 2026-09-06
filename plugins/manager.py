from fastapi import Request
from fastapi.responses import HTMLResponse
from bson import ObjectId

def setup(app, bot, db, config):

    # ১. অ্যাডমিন ড্যাশবোর্ড পেজ (URL: /admin)
    @app.get("/admin", response_class=HTMLResponse)
    async def serve_admin_panel():
        with open("admin.html", "r", encoding="utf-8") as f:
            return f.read()

    # ২. অ্যাডমিন লগইন
    @app.post("/api/admin/login")
    async def admin_login(req: Request):
        data = await req.json()
        if data.get("password") == config.ADMIN_PASSWORD:
            return {"success": True}
        return {"success": False}

    # ৩. সব ভিডিও লিস্ট পাওয়া
    @app.get("/api/videos")
    async def get_videos():
        videos = await db.videos.find().to_list(length=300)
        for v in videos:
            v["_id"] = str(v["_id"])
        return videos

    # ৪. ভিডিও এডিট (থাম্বনেইল, টাইটেল, বাটন)
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
        return {"status": "success"}

    # ৫. ভিডিও ডিলিট
    @app.delete("/api/admin/delete-video/{vid_id}")
    async def delete_video(vid_id: str):
        await db.videos.delete_one({"_id": ObjectId(vid_id)})
        return {"status": "success"}

    # ৬. ডিরেক্ট লিংক লিস্ট
    @app.get("/api/admin/links")
    async def get_links():
        links = await db.direct_links.find().to_list(length=100)
        for l in links:
            l["_id"] = str(l["_id"])
        return links

    # ৭. নতুন ডিরেক্ট লিংক যোগ করা
    @app.post("/api/admin/add-link")
    async def add_link(req: Request):
        data = await req.json()
        url = data.get("url")
        if url:
            await db.direct_links.insert_one({"url": url.strip(), "clicks": 0})
            return {"status": "success"}
        return {"status": "error"}

    # ৮. ডিরেক্ট লিংক ডিলিট
    @app.delete("/api/admin/delete-link/{link_id}")
    async def delete_link(link_id: str):
        await db.direct_links.delete_one({"_id": ObjectId(link_id)})
        return {"status": "success"}
