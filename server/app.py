"""薄いサーバー。API キーを持つ中継役で、杯を受け取ってコーチに診断させ、結果を返す。

  POST /cups       multipart: meta(JSON) + photo(JPEG) → 202 {"cup_id"}
  GET  /cups/{id}  → {"status": "diagnosing"|"done"|"failed", "diagnosis"?, "error"?}

杯の記録は server/data/cups/ に置く（git 管理外）。音声は受け取らない。
起動: cd server && uv run uvicorn app:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import json
import os
import logging
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile

import coach
import memory
import params
import review
import sound_picture

log = logging.getLogger("uvicorn.error")
DATA = Path(__file__).parent / "data" / "cups"
DATA.mkdir(parents=True, exist_ok=True)
# 練習の音を通しで置く（D21）。practices/<練習ID>/<区間番号>.wav。杯の区間は杯のフォルダにも同じものを置く
PRACTICES = Path(__file__).parent / "data" / "practices"
PRACTICES.mkdir(parents=True, exist_ok=True)


def _practice_path(practice_id: str, seq: int) -> Path:
    try:
        uuid.UUID(practice_id)
    except ValueError:
        raise HTTPException(400, "bad practice id")
    d = PRACTICES / practice_id
    d.mkdir(exist_ok=True)
    return d / f"{int(seq):03d}.wav"

app = FastAPI(title="Steam Coach")


@app.on_event("startup")
def resume_unfinished() -> None:
    """サーバーが診断の途中で止まった杯を、起動時に診断し直す"""
    import threading
    for d in DATA.iterdir():
        status = d / "status.json"
        if status.exists() and json.loads(status.read_text()).get("status") == "diagnosing":
            log.info("resume diagnosis: %s", d.name)
            threading.Thread(target=_run, args=(d.name,), daemon=True).start()


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
        if s.get("duplicate_of"):  # 二重に届いた杯は比較に使わない
            continue
        if s.get("status") == "done" and s.get("received_at", "") < before:
            done.append((s["received_at"], d))
    if not done:
        return None
    _, d = max(done)
    meta = json.loads((d / "meta.json").read_text())
    s = json.loads((d / "status.json").read_text())
    feats = dict(meta["features"]) if meta.get("features") else None
    if feats is not None:
        feats["params_version"] = meta.get("params_version", 0)
    return {"ended_at": meta.get("ended_at"), "features": feats,
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
        audio_path = d / "audio.wav"
        features = dict(meta["features"]) if meta.get("features") else None
        if features is not None:
            features["params_version"] = meta.get("params_version", 0)  # 0 は版の仕組みより前の杯
        # 音があれば、今の判定の版で測り直してから診断する（D21）。アプリが出した値は features_app に残す
        if audio_path.exists():
            try:
                import rejudge
                cur = params.current()
                rj = rejudge.judge(audio_path, cur["values"], meta.get("background"))
                if rj.get("features"):
                    start = meta.get("audio_start_sec") or 0.0
                    meta["features_app"] = meta.get("features")
                    meta["features"] = rj["features"]
                    meta["marks_app"] = meta.get("marks")
                    meta["marks"] = {k: v + start for k, v in (rj.get("marks") or {}).items()}  # 包絡の先頭からの秒に直す
                    meta["params_version"] = cur["version"]
                    meta["rejudged_at"] = datetime.now().isoformat()
                    _write(d / "meta.json", meta)
                    features = dict(rj["features"], params_version=cur["version"])
            except Exception:
                log.exception("rejudge failed: %s", cup_id)
        try:
            png = sound_picture.draw(meta.get("envelope") or [], meta.get("marks"),
                                     f"{status['received_at'][:16].replace('T', ' ')} の杯",
                                     audio=audio_path.read_bytes() if audio_path.exists() else None,
                                     audio_start_sec=meta.get("audio_start_sec") or 0.0)
        except Exception:
            log.exception("sound picture failed: %s", cup_id)
            png = None
        if png:
            (d / "sound.png").write_bytes(png)
            pictures.append(("今回の杯の音の絵", png))
        result = coach.diagnose(features, meta.get("self_rating"), photo, previous, pictures)
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


@app.post("/practices/{practice_id}/audio/{seq}")
async def practice_audio(practice_id: str, seq: int, audio: UploadFile = File(...)) -> dict:
    """杯につかない練習の音（終了時の最後の区間）。練習の音を通しで残すため"""
    p = _practice_path(practice_id, seq)
    p.write_bytes(await audio.read())
    return {"ok": True, "path": f"{practice_id}/{p.name}"}


@app.get("/params")
def get_params() -> dict:
    """アプリが練習の開始時に取りに来る判定の閾値（今の版）"""
    c = params.current()
    return {"version": c["version"], "values": c["values"]}


@app.get("/params/proposal")
def get_proposal() -> dict:
    """コーチの判定の調整の提案（承認待ち）。なければ proposal は null"""
    p = params.proposal()
    return {"proposal": p, "current_version": params.current()["version"],
            "means": {k: s["means"] for k, s in params.SPEC.items()}}


@app.post("/params/proposal/{decision}")
def decide_proposal(decision: str) -> dict:
    """本人が提案を適用する（accept）か見送る（reject）"""
    import anthropic
    if decision not in ("accept", "reject"):
        raise HTTPException(404, "not found")
    try:
        result = params.decide(decision == "accept")
    except ValueError as e:
        raise HTTPException(409, str(e))
    p = result["proposal"]
    when = datetime.now().strftime("%Y-%m-%d %H:%M")
    if result["accepted"]:
        line = f"{when}: v{result['version']} を本人が承認して適用。{p['changes']}（前 {p['before']}）。理由: {p['reason']}"
    else:
        line = f"{when}: 提案 {p['changes']} を本人が見送った。理由として出していたこと: {p['reason']}"
    memory.note_params(anthropic.Anthropic(), line)
    return {"accepted": result["accepted"], "version": params.current()["version"]}


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
                     photo: Optional[UploadFile] = File(None), audio: Optional[UploadFile] = File(None)) -> dict:
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
    if audio is not None:
        # 前回の区切りからこの杯までの音を全部。自宅のこの Mac にだけ置き、Claude には渡さない（D21）
        (d / "audio.wav").write_bytes(await audio.read())
        if meta_obj.get("practice_id") is not None and meta_obj.get("segment_seq") is not None:
            p = _practice_path(meta_obj["practice_id"], meta_obj["segment_seq"])
            if not p.exists():
                os.link(d / "audio.wav", p)  # 同じ中身をハードリンクで置く（容量を食わない）
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
