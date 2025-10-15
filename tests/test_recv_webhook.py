from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
# from pyngrok import ngrok
import nest_asyncio
import os
from threading import Thread

# nest_asyncio.apply()
# ngrok.set_auth_token("2DZJxchW8l7QYl2r9kVBY30k87Y_75d18xJmDYJwYLap5F89Q")

# public_url = ngrok.connect(8000).public_url
# print("Public URL:", public_url)

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return {"message": "FastAPI server is running"}

# @app.get("/zalo_verifierJCVd9ipjLG0oakSjkU4r3cNFe3U9kNTXC34o.html")
# async def zalo_verifier():
#     file_path = "static/zalo_verifierJCVd9ipjLG0oakSjkU4r3cNFe3U9kNTXC34o.html"
#     if not os.path.exists(file_path):
#         raise HTTPException(status_code=404, detail="Verification file not found")
#     return FileResponse(file_path, media_type="text/html")

@app.post("/webhook-zalooa")
async def webhook_zalooa_post(request: Request):
    data = await request.json()
    print("Received webhook data (zalooa):")
    print(data)
    return {"message": "Webhook received successfully."}

if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=5544)