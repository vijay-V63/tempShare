# tempShare
TempShare — Share text and files temporarily with a simple code. Send anything (notes, code, documents, images, etc.) to another device without creating accounts or long-term storage. Just paste, generate a code, and share it. Everything automatically deletes after 30 minutes for complete privacy.

# TempShare - Temporary File & Text Sharing

A simple, fast, and secure way to share text and files between devices that **automatically expires after 30 minutes**.

![TempShare](https://via.placeholder.com/800x400/6366f1/ffffff?text=TempShare)

## Features

- **No signup required** — Instant sharing
- **Text & File sharing** — Share notes, code, documents, images, etc.
- **Auto deletion** — All data is automatically deleted after 30 minutes
- **Responsive UI** — Works perfectly on mobile and desktop
- **Clean & Modern Interface**
- **Privacy Focused** — No accounts, no long-term storage

## How to Use

1. **Create Share**
   - Paste your text or attach a file
   - Click "Generate Code"
   - Copy the generated 8-character code

2. **Share the Code**
   - Send the code to your friend/colleague via any messaging app

3. **Retrieve Content**
   - Go to the app and enter the code
   - View or download the content before it expires

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: HTML + Tailwind CSS + Vanilla JS
- **Storage**: Vercel KV (Redis) with TTL
- **Deployment**: Vercel
- **File Storage**: Vercel Blob (planned)

## Local Development

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd tempShare

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
uvicorn main:app --reload
