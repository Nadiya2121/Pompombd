from fastapi import Request
from fastapi.responses import HTMLResponse
from bson import ObjectId

def setup(app, bot, db, config):

    # ১. সুপার অ্যাডমিন ড্যাশবোর্ড পেজ (URL: /admin)
    @app.get("/admin", response_class=HTMLResponse)
    async def serve_admin_panel():
        with open("admin.html", "r", encoding="utf-8") as f:
            return f.read()

    # ২. অ্যাডমিন লগইন ভেরিফিকেশন
    @app.post("/api/admin/login")
    async def admin_login(req: Request):
        data = await req.json()
        if data.get("password") == config.ADMIN_PASSWORD:
            return {"success": True}
        return {"success": False}

    # ৩. অ্যানালিটিক্স পরিসংখ্যান API
    @app.get("/api/admin/stats")
    async def get_stats():
        users_count = await db.analytics.find_one({"type": "traffic"})
        series_count = await db.series.count_documents({})
        links_count = await db.direct_links.count_documents({})
        
        return {
            "users": users_count.get("active_users", 0) if users_count else 0,
            "ad_clicks": users_count.get("total_ad_clicks", 0) if users_count else 0,
            "videos": series_count,
            "links": links_count
        }

    # ৪. পুরো সিরিজ ডিলিট (সিরিজের সাথে সাথে এর সব পার্ট ডিলিট হবে)
    @app.delete("/api/admin/delete-series/{series_id}")
    async def delete_series(series_id: str):
        try:
            s_id = ObjectId(series_id)
            await db.series.delete_one({"_id": s_id})
            await db.video_parts.delete_many({"series_id": s_id})
            return {"status": "success", "message": "পুরো সিরিজ ও সব পার্ট ডিলিট হয়েছে!"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ৫. সিরিজের ভেতরের নির্দিষ্ট একটি পার্ট ডিলিট করা
    @app.delete("/api/admin/delete-part/{part_id}")
    async def delete_single_part(part_id: str):
        try:
            await db.video_parts.delete_one({"_id": ObjectId(part_id)})
            return {"status": "success", "message": "পার্টটি ডিলিট হয়েছে!"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ৬. সিরিজ এডিট (টাইটেল এবং থাম্বনেইল)
    @app.post("/api/admin/edit-video")
    async def edit_video(req: Request):
        data = await req.json()
        vid_id = data.get("id")
        await db.series.update_one(
            {"_id": ObjectId(vid_id)},
            {"$set": {
                "title": data.get("title"),
                "thumbnail": data.get("thumbnail")
            }}
        )
        return {"status": "success"}

    # ৭. ডিরেক্ট লিংকগুলো লিস্ট করা
    @app.get("/api/admin/links")
    async def get_links():
        links = await db.direct_links.find().to_list(length=200)
        for l in links:
            l["_id"] = str(l["_id"])
        return links

    # ৮. নতুন ডিরেক্ট লিংক যোগ করা
    @app.post("/api/admin/add-link")
    async def add_link(req: Request):
        data = await req.json()
        url = data.get("url")
        if url:
            await db.direct_links.insert_one({"url": url.strip(), "clicks": 0})
            return {"status": "success"}
        return {"status": "error"}

    # ৯. ডিরেক্ট লিংক ডিলিট করা
    @app.delete("/api/admin/delete-link/{link_id}")
    async def delete_link(link_id: str):
        await db.direct_links.delete_one({"_id": ObjectId(link_id)})
        return {"status": "success"}
