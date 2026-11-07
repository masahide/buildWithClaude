"""薄いサーバー。API キーを持つ中継役で、杯を受け取ってコーチに診断させ、結果を返す。

  POST /cups       multipart: meta(JSON) + photo(JPEG) → 202 {"cup_id"}
  GET  /cups/{id}  → {"status": "diagnosing"|"done"|"failed", "diagnosis"?, "error"?}

杯の記録は server/data/cups/ に置く（git 管理外）。音声は受け取らない。
起動: cd server && uv run uvicorn app:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile

import coach
import memory
import review
import sound_picture

log = logging.getLogger("uvicorn.error")
DATA = Path(__file__).parent / "data" / "cups"
DATA.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Steam Coach")


def _dir(cup_id: str) -> Path:
    # パスに使うので UUID 以外は受け付けない
    try:
        uuid.UUID(cup_id)
    except ValueError:
        raise HTTPException(404, "not found")
    return DATA / cup_id


def _write(path: Path, obj: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2))
    tmp.replace(path)


def _previous_cup(before: str) -> Optional[dict]:
    """直前に診断が済んだ杯。予測の当否を判定させるために渡す。"""
    done = []
    for d in DATA.iterdir():
        status = d / "status.json"
        if not status.exists():
            continue
        s = json.loads(status.read_text())
        if s.get("status") == "done" and s.get("received_at", "") < before:
            done.append((s["received_at"], d))
    if not done:
        return None
    _, d = max(done)
    meta = json.loads((d / "meta.json").read_text())
    s = json.loads((d / "status.json").read_text())
    return {"ended_at": meta.get("ended_at"), "features": meta.get("features"),
            "self_rating": meta.get("self_rating"), "diagnosis": s.get("diagnosis"), "_dir": str(d)}


def _run(cup_id: str) -> None:
    d = DATA / cup_id
    meta = json.loads((d / "meta.json").read_text())
    status = json.loads((d / "status.json").read_text())
    photo_path = d / "photo.jpg"
    photo = photo_path.read_bytes() if photo_path.exists() else None
    started = time.monotonic()
    try:
        previous = _previous_cup(status["received_at"])
        pictures: list[tuple[str, bytes]] = []
        prev_png = Path(previous.pop("_dir")) / "sound.png" if previous else None
        if prev_png and prev_png.exists():
            pictures.append(("前の杯の音の絵", prev_png.read_bytes()))
        try:
            png = sound_picture.draw(meta.get("envelope") or [], meta.get("marks"),
                                     f"{status['received_at'][:16].replace('T', ' ')} の杯")
        except Exception:
            log.exception("sound picture failed: %s", cup_id)
            png = None
        if png:
            (d / "sound.png").write_bytes(png)
            pictures.append(("今回の杯の音の絵", png))
        result = coach.diagnose(meta.get("features"), meta.get("self_rating"), photo, previous, pictures)
        status.update(status="done", diagnosis=result.model_dump())
    except Exception as e:  # 失敗はアプリに返して表示する
        log.exception("diagnosis failed: %s", cup_id)
        status.update(status="failed", error=str(e))
    status["elapsed_sec"] = round(time.monotonic() - started, 2)
    log.info("cup %s %s in %.1fs", cup_id, status["status"], status["elapsed_sec"])
    _write(d / "status.json", status)


@app.get("/coach")
def coach_notes() -> dict:
    """アプリに見せるコーチの記憶（今日のテーマ、あなたの正解、コーチが学んだこと）"""
    import anthropic
    notes = memory.read_all(anthropic.Anthropic())
    return {"today": notes.get("/today.md", ""), "rules": notes.get("/rules.md", ""),
            "reading": notes.get("/reading.md", ""), "tendencies": notes.get("/tendencies.md", "")}


@app.post("/teach")
def teach(text: str = Form(...)) -> dict:
    """本人がコーチに教える（例:「27〜32秒は追加の泡入れだった」）。コーチの記憶に日付つきで残る"""
    import anthropic
    if not text.strip():
        raise HTTPException(400, "text is empty")
    memory.teach(anthropic.Anthropic(), text, datetime.now().strftime("%Y-%m-%d %H:%M"))
    return {"ok": True}


@app.post("/review", status_code=202)
def start_review(background: BackgroundTasks, day: Optional[str] = None) -> dict:
    """夜の振り返りを裏で回す。結果は data/reviews/ に残る"""
    from datetime import date
    d = date.fromisoformat(day) if day else date.today()

    def job() -> None:
        out = DATA.parent / "reviews"
        out.mkdir(exist_ok=True)
        try:
            result = review.run(d)
        except Exception as e:
            log.exception("review failed")
            result = {"day": d.isoformat(), "error": str(e)}
        (out / f"{d.isoformat()}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
        log.info("review %s done", d.isoformat())

    background.add_task(job)
    return {"day": d.isoformat(), "status": "started"}


@app.get("/cups/{cup_id}/sound.png")
def cup_sound(cup_id: str):
    """杯ごとの音の絵（README・デモ・本人の確認用）"""
    from fastapi.responses import Response
    p = _dir(cup_id) / "sound.png"
    if not p.exists():
        raise HTTPException(404, "not found")
    return Response(p.read_bytes(), media_type="image/png")


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/cups", status_code=202)
async def create_cup(background: BackgroundTasks, meta: str = Form(...),
                     photo: Optional[UploadFile] = File(None)) -> dict:
    try:
        meta_obj = json.loads(meta)
    except json.JSONDecodeError:
        raise HTTPException(400, "meta must be JSON")
    cup_id = str(uuid.uuid4())
    d = DATA / cup_id
    d.mkdir()
    _write(d / "meta.json", meta_obj)
    if photo is not None:
        (d / "photo.jpg").write_bytes(await photo.read())
    _write(d / "status.json", {"status": "diagnosing", "received_at": datetime.now().isoformat()})
    background.add_task(_run, cup_id)
    return {"cup_id": cup_id}


@app.get("/cups/{cup_id}")
def get_cup(cup_id: str) -> dict:
    status = _dir(cup_id) / "status.json"
    if not status.exists():
        raise HTTPException(404, "not found")
    s = json.loads(status.read_text())
    return {k: s[k] for k in ("status", "diagnosis", "error", "elapsed_sec") if k in s}
