import os
import re
import glob
import uuid
import asyncio
import uvicorn
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

try:
    import static_ffmpeg
    static_ffmpeg.add_paths()
except Exception:
    pass

from app.downloader import DownloaderEngine, DOWNLOAD_DIR
from app.utils import sanitize_url

app = FastAPI(title="Pro Video Downloader Web")

DOWNLOAD_SEMAPHORE = asyncio.Semaphore(5)

# အချိန်နဲ့တပြေးညီ Progress ဒေတာများ သိမ်းဆည်းမည့် Cache
PROGRESS_DATA = {}

os.makedirs("downloads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

def clean_orphaned_files():
    try:
        part_files = glob.glob(os.path.join(DOWNLOAD_DIR, "*.part"))
        for f in part_files:
            try:
                os.remove(f)
            except Exception:
                pass
    except Exception:
        pass

clean_orphaned_files()

class InspectRequest(BaseModel):
    url: str

class StartDownloadRequest(BaseModel):
    url: str
    quality: str = "720"

def remove_temp_file(path: str):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        print(f"Error removing file {path}: {e}")

@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.post("/api/inspect")
async def inspect_video(payload: InspectRequest):
    if not payload.url:
        raise HTTPException(status_code=400, detail="URL လိပ်စာ ထည့်သွင်းပေးပါ")
    
    clean_url = sanitize_url(payload.url)
    try:
        data = await run_in_threadpool(DownloaderEngine.get_info, clean_url)
        return JSONResponse(content={"success": True, "data": data})
    except Exception as e:
        return JSONResponse(status_code=400, content={"success": False, "message": str(e)})

# ⭐️ Progress စောင့်ကြည့်နိုင်မည့် Download Task စတင်ခြင်း ⭐️
@app.post("/api/start-download")
async def start_download_task(payload: StartDownloadRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())[:8]
    PROGRESS_DATA[task_id] = {
        "status": "starting",
        "percent": "0%",
        "speed": "0 KiB/s",
        "eta": "--:--",
        "file_path": None,
        "filename": None,
        "error": None
    }

    def sync_download_worker():
        def ytdl_hook(d):
            if d['status'] == 'downloading':
                p_str = re.sub(r'\x1b\[[0-9;]*m', '', d.get('_percent_str', '0%')).strip()
                s_str = re.sub(r'\x1b\[[0-9;]*m', '', d.get('_speed_str', '0 KiB/s')).strip()
                e_str = re.sub(r'\x1b\[[0-9;]*m', '', d.get('_eta_str', '--:--')).strip()
                PROGRESS_DATA[task_id].update({
                    "status": "downloading",
                    "percent": p_str,
                    "speed": s_str,
                    "eta": e_str
                })
            elif d['status'] == 'finished':
                PROGRESS_DATA[task_id]["status"] = "processing"

        try:
            clean_url = sanitize_url(payload.url)
            file_path, safe_title = DownloaderEngine.process_download(clean_url, payload.quality, progress_hook=ytdl_hook)
            ext = os.path.splitext(file_path)[1]
            PROGRESS_DATA[task_id].update({
                "status": "completed",
                "file_path": file_path,
                "filename": f"{safe_title}{ext}"
            })
        except Exception as e:
            PROGRESS_DATA[task_id].update({
                "status": "error",
                "error": str(e)
            })

    background_tasks.add_task(sync_download_worker)
    return JSONResponse(content={"success": True, "task_id": task_id})

# ⭐️ ဖုန်းမှ Progress အချိန်နဲ့တပြေးညီ လှမ်းမေးမည့် Endpoint ⭐️
@app.get("/api/progress/{task_id}")
async def get_progress(task_id: str):
    if task_id not in PROGRESS_DATA:
        raise HTTPException(status_code=404, detail="Task not found")
    return JSONResponse(content=PROGRESS_DATA[task_id])

# ⭐️ ဒေါင်းလုဒ်ပြီးသွားပါက ဖိုင်ကို ဖုန်းထဲသို့ အပြီးသတ် ပို့ပေးမည့် Endpoint ⭐️
@app.get("/api/fetch-file/{task_id}")
async def fetch_finished_file(task_id: str, background_tasks: BackgroundTasks):
    task = PROGRESS_DATA.get(task_id)
    if not task or task.get("status") != "completed":
        raise HTTPException(status_code=400, detail="File is not ready yet")

    file_path = task["file_path"]
    filename = task["filename"]

    # ဖိုင်ပို့ပြီးပါက Server ပေါ်မှ အလိုအလျောက် ပြန်ဖျက်ပေးခြင်း
    background_tasks.add_task(remove_temp_file, file_path)
    background_tasks.add_task(PROGRESS_DATA.pop, task_id, None)

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='application/octet-stream'
    )

if __name__ == "__main__":
        # Cloud ပေါ်တွင် Auto Port ရယူပြီး Local တွင် 8080 ဖြင့် အလုပ်လုပ်စေခြင်း
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("run:app", host="0.0.0.0", port=port, access_log=False, reload=False)