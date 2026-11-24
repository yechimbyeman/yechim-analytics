"""Export public YECHIM channel for visual audit; never reads customer chats."""
import asyncio
import csv
import io
import json
import os
import subprocess
import tempfile
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageOps
from supabase import create_client
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import Channel

CHANNEL = "yechimbor"
BUCKET = "yechim-brandbook-audit"
TZ = ZoneInfo("Asia/Tashkent")
FIELDS = ["id", "date", "url", "album_id", "text", "views", "forwards", "reactions", "media_type", "visual_status", "visual_files", "captured_at"]

def env(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError("Missing configuration: " + name)
    return value

def csv_bytes(rows):
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=FIELDS)
    writer.writeheader()
    for row in rows:
        # Prevent spreadsheet formula injection in user-authored fields.
        writer.writerow({k: ("'" + v if isinstance(v, str) and v.startswith(("=", "+", "-", "@", "\t", "\r")) else v) for k, v in row.items()})
    return buf.getvalue().encode("utf-8-sig")

def save_image(source, target):
    with Image.open(source) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        im.thumbnail((1100, 1100))
        im.save(target, "JPEG", quality=82, optimize=True)

def make_sheets(images, dest):
    paths = []
    for start in range(0, len(images), 36):
        batch = images[start:start+36]
        canvas = Image.new("RGB", (6*220, 6*250), "#eeeeee")
        draw = ImageDraw.Draw(canvas)
        for i, p in enumerate(batch):
            x, y = (i % 6)*220, (i // 6)*250
            with Image.open(p) as im:
                im.thumbnail((208, 215))
                canvas.paste(im, (x+(220-im.width)//2, y+(215-im.height)//2))
            draw.text((x+8, y+220), p.stem, fill="black")
        out = dest / f"sheet_{start//36+1:03}.jpg"
        canvas.save(out, quality=88, optimize=True)
        paths.append(out)
    return paths

async def extract(client, msg, target, tmp):
    if msg.photo:
        raw = await client.download_media(msg, file=bytes)
        if raw:
            out = target / f"{msg.id}_photo.jpg"
            save_image(io.BytesIO(raw), out)
            return "photo", "ok", [out]
        return "photo", "unavailable", []
    doc = msg.document
    mime = getattr(doc, "mime_type", "") or ""
    if doc and mime.startswith("image/"):
        if getattr(doc, "size", 0) > 30*1024*1024:
            return "image_document", "size_limit", []
        raw = await client.download_media(msg, file=bytes)
        if raw:
            out = target / f"{msg.id}_image.jpg"
            save_image(io.BytesIO(raw), out)
            return "image_document", "ok", [out]
        return "image_document", "unavailable", []
    if doc and mime.startswith("video/"):
        # Prefer Telegram's thumbnail; sample the actual video only up to 60 MB.
        paths = []
        try:
            raw = await client.download_media(msg, file=bytes, thumb=-1)
            if raw:
                out = target / f"{msg.id}_thumb.jpg"
                save_image(io.BytesIO(raw), out)
                paths.append(out)
        except Exception:
            pass
        if 0 < getattr(doc, "size", 0) <= 60*1024*1024:
            with tempfile.TemporaryDirectory(dir=tmp) as work:
                video = await client.download_media(msg, file=str(Path(work)/"video"))
                if video:
                    probe = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",video], capture_output=True, text=True, timeout=30)
                    try:
                        duration = float(probe.stdout.strip())
                    except ValueError:
                        duration = 0
                    if duration > 0:
                        for n, ratio in enumerate((0.1, 0.5, 0.9), 1):
                            frame = Path(work)/f"frame{n}.jpg"
                            subprocess.run(["ffmpeg","-nostdin","-loglevel","error","-y","-ss",str(duration*ratio),"-i",video,"-frames:v","1","-vf","scale=1100:1100:force_original_aspect_ratio=decrease",str(frame)], capture_output=True, timeout=45)
                            if frame.exists():
                                out = target / f"{msg.id}_frame{n}.jpg"
                                save_image(frame, out)
                                paths.append(out)
        status = "sampled" if any("_frame" in p.name for p in paths) else "thumbnail_only" if paths else "unavailable"
        return "video", status, paths
    return ("other" if msg.media else "text"), "not_applicable", []

def upload(storage, name, data, mime):
    storage.upload(name, data, {"content-type": mime, "upsert": "true"})

async def main():
    start = datetime.fromisoformat(env("AUDIT_FROM")).replace(tzinfo=TZ)
    end = datetime.fromisoformat(env("AUDIT_TO")).replace(tzinfo=TZ)
    if end <= start:
        raise ValueError("AUDIT_TO must be after AUDIT_FROM (exclusive)")
    db = create_client(env("NEXT_PUBLIC_SUPABASE_URL"), env("SUPABASE_SERVICE_ROLE_KEY"))
    buckets = db.storage.list_buckets()
    bucket = next((b for b in buckets if b.name == BUCKET), None)
    if bucket is None:
        db.storage.create_bucket(BUCKET, options={"public": False})
        bucket = db.storage.get_bucket(BUCKET)
    if bucket.public is not False:
        raise RuntimeError("Audit bucket is not private; refusing upload")
    storage = db.storage.from_(BUCKET)
    client = TelegramClient(StringSession(env("TELEGRAM_SESSION_STRING")), int(env("TELEGRAM_API_ID")), env("TELEGRAM_API_HASH"))
    await client.connect()
    try:
        if not await client.is_user_authorized():
            raise RuntimeError("Existing Telegram session is not authorized")
        channel = await client.get_entity(CHANNEL)
        if not isinstance(channel, Channel) or not channel.broadcast or (channel.username or "").lower() != CHANNEL:
            raise RuntimeError("Unexpected source; refusing export")
        captured = datetime.now(timezone.utc).isoformat()
        prefix = f"{start.date()}_to_{end.date()}/{env('GITHUB_RUN_ID')}-{env('GITHUB_RUN_ATTEMPT')}"
        rows = defaultdict(list)
        visuals = defaultdict(list)
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            async for msg in client.iter_messages(channel, reverse=True, offset_date=start):
                if msg.date < start:
                    continue
                if msg.date >= end:
                    break
                if msg.action:
                    continue
                month = msg.date.astimezone(TZ).strftime("%Y-%m")
                dest = root / month
                dest.mkdir(exist_ok=True)
                try:
                    kind, status, paths = await extract(client, msg, dest, root)
                except Exception as exc:
                    kind, status, paths = "media", "error:"+type(exc).__name__, []
                reactions = []
                for r in getattr(getattr(msg, "reactions", None), "results", []) or []:
                    reaction = r.reaction
                    reactions.append({"reaction": getattr(reaction,"emoticon",None) or str(getattr(reaction,"document_id","unknown")), "count": r.count})
                row = dict(id=msg.id, date=msg.date.astimezone(TZ).isoformat(), url=f"https://t.me/{CHANNEL}/{msg.id}", album_id=str(msg.grouped_id or ""), text=msg.message or "", views=msg.views, forwards=msg.forwards, reactions=json.dumps(reactions, ensure_ascii=False), media_type=kind, visual_status=status, visual_files=";".join(p.name for p in paths), captured_at=captured)
                rows[month].append(row)
                visuals[month].extend(paths)
                if sum(map(len, rows.values())) % 100 == 0:
                    print("Processed", sum(map(len, rows.values())), "channel messages", flush=True)
            all_rows = []
            for month in sorted(rows):
                all_rows.extend(rows[month])
                dest = root/month
                sheets = make_sheets(visuals[month], dest)
                upload(storage, f"{prefix}/{month}/posts.csv", csv_bytes(rows[month]), "text/csv")
                for sheet in sheets:
                    upload(storage, f"{prefix}/{month}/{sheet.name}", sheet.read_bytes(), "image/jpeg")
                # Small archives: split full-size previews into <= 20 MB groups.
                batch, size, part = [], 0, 1
                for p in visuals[month]:
                    n = p.stat().st_size
                    if batch and size+n > 20*1024*1024:
                        send_zip(storage, prefix, month, part, batch)
                        batch, size, part = [], 0, part+1
                    batch.append(p)
                    size += n
                if batch:
                    send_zip(storage, prefix, month, part, batch)
            upload(storage, f"{prefix}/all_posts.csv", csv_bytes(all_rows), "text/csv")
            summary = {"source": CHANNEL, "from": str(start.date()), "to_exclusive": str(end.date()), "captured_at": captured, "messages":len(all_rows), "visuals":sum(map(len,visuals.values())), "months":{m:len(v) for m,v in rows.items()}, "status_counts":{s:sum(r["visual_status"]==s for r in all_rows) for s in sorted({r["visual_status"] for r in all_rows})}}
            upload(storage, f"{prefix}/summary.json", json.dumps(summary,ensure_ascii=False,indent=2).encode(), "application/json")
            print("Export complete. Private storage folder:", prefix, "| messages:", len(all_rows), "| previews:", summary["visuals"])
    finally:
        await client.disconnect()

def send_zip(storage, prefix, month, part, paths):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as z:
        for p in paths:
            z.write(p, p.name)
    upload(storage, f"{prefix}/{month}/previews_{part:03}.zip", buf.getvalue(), "application/zip")

if __name__ == "__main__":
    asyncio.run(main())
