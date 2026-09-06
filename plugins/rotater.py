import random

def setup(app, bot, db, config):

    @app.get("/api/get-ad-link")
    async def get_ad_link():
        links = await db.direct_links.find({}).to_list(length=100)
        
        # কোনো লিংক না থাকলে ব্যাকআপ গুগল
        if not links:
            return {"url": "https://google.com"}

        # স্মার্ট রোটেশন: র‍্যান্ডমলি একেক সময় একেকটি লিংক যাবে
        selected = random.choice(links)
        await db.direct_links.update_one({"_id": selected["_id"]}, {"$inc": {"clicks": 1}})
        
        return {"url": selected["url"]}
