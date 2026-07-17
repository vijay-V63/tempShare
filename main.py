from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import os
from datetime import datetime, timedelta
from nanoid import generate
import json
from vercel_blob import put

app = FastAPI(title="TempShare")

app.mount("/static", StaticFiles(directory="static"), name="static")

# KV or Fake
class FakeRedis:
    def __init__(self):
        self.store = {}
    async def set(self, key, value, ex=None):
        self.store[key] = {"value": value, "expires": datetime.utcnow().timestamp() + (ex or 1800)}
        return "OK"
    async def get(self, key):
        data = self.store.get(key)
        if not data or datetime.utcnow().timestamp() > data["expires"]:
            self.store.pop(key, None)
            return None
        return data["value"]
    async def delete(self, key):
        return self.store.pop(key, None) is not None

redis = FakeRedis()

@app.get("/", response_class=HTMLResponse)
async def home():
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/create")
async def create_clipboard(
    text: str = Form(None),
    file: UploadFile = File(None)
):
    code = generate(size=8).upper()
    expires_in = 30 * 60

    data = {
        "code": code,
        "text": text or "",
        "expires_at": int((datetime.utcnow() + timedelta(seconds=expires_in)).timestamp())
    }

    if file and file.size > 0:
        # Upload to Vercel Blob
        file_content = await file.read()
        blob = await put(f"uploads/{code}-{file.filename}", file_content, {
            "access": "private",
            "addRandomSuffix": False
        })
        data["file_url"] = blob.url
        data["file_name"] = file.filename
        data["file_size"] = file.size

    await redis.set(code, json.dumps(data), ex=expires_in)

    return {"success": True, "code": code}

@app.get("/api/retrieve/{code}")
async def get_clipboard(code: str):
    raw_data = await redis.get(code)
    if not raw_data:
        raise HTTPException(status_code=404, detail="Expired or not found")
    data = json.loads(raw_data)
    if datetime.utcnow().timestamp() > data.get("expires_at", 0):
        await redis.delete(code)
        raise HTTPException(status_code=404, detail="Expired")
    return data

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
