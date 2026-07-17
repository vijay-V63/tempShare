from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime, timedelta
from nanoid import generate
import json
from vercel_blob import put, get

app = FastAPI(title="TempShare")
app.mount("/static", StaticFiles(directory="static"), name="static")

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
        file_content = await file.read()
        pathname = f"uploads/{code}-{file.filename}"
        
        # put() returns: BlobObject(url, pathname, contentType, size)
        blob = await put(pathname, file_content, {"access": "private"})
        
        # Store pathname for private blob retrieval
        data["file_pathname"] = blob.pathname
        data["file_name"] = file.filename
        data["file_size"] = file.size

    await redis.set(code, json.dumps(data), ex=expires_in)
    return JSONResponse({"success": True, "code": code})

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

@app.get("/download/{code}")
async def download_file(code: str):
    raw_data = await redis.get(code)
    if not raw_data:
        raise HTTPException(status_code=404, detail="Not found")
    data = json.loads(raw_data)
    
    if "file_pathname" not in data:
        raise HTTPException(status_code=404, detail="No file")
    
    # get() for private blobs returns: Blob(body, contentType, size)
    blob = await get(data["file_pathname"], {"access": "private"})
    
    return StreamingResponse(
        blob.body,
        media_type=blob.contentType,
        headers={
            "Content-Disposition": f"attachment; filename={data['file_name']}",
            "Cache-Control": "private, no-cache",
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
