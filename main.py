from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime, timedelta
from nanoid import generate
import json
import httpx  # Add this to requirements.txt!

app = FastAPI(title="TempShare")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Only import put from vercel_blob
from vercel_blob import put

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

async def download_blob(pathname: str) -> tuple:
    """Download private blob using Vercel Blob API"""
    import os
    token = os.environ.get("BLOB_READ_WRITE_TOKEN")
    if not token:
        raise HTTPException(status_code=500, detail="BLOB_READ_WRITE_TOKEN not set")
    
    url = f"https://blob.vercel-storage.com/{pathname}"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Blob not found")
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Blob error: {response.status_code}")
        
        content_type = response.headers.get("content-type", "application/octet-stream")
        return response.content, content_type

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
        
        blob = await put(pathname, file_content, {"access": "private"})
        
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
    
    # Use our custom download function
    content, content_type = await download_blob(data["file_pathname"])
    
    return StreamingResponse(
        iter([content]),  # Stream the bytes
        media_type=content_type,
        headers={
            "Content-Disposition": f"attachment; filename={data['file_name']}",
            "Cache-Control": "private, no-cache",
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
