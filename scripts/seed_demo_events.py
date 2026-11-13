#!/usr/bin/env python3
"""Hasilkan event demo untuk event store dashboard.

Build ini tidak menyertakan mesin deteksi, jadi event store tetap kosong tanpa
bantuan skrip ini. Skrip menulis event berformat ``vision.event.v1`` ke
``outputs/events.jsonl`` agar dashboard punya data untuk ditampilkan dan diuji.

Contoh:
    .venv/bin/python scripts/seed_demo_events.py
    .venv/bin/python scripts/seed_demo_events.py --camera 1.145-CH13 --count 10
    .venv/bin/python scripts/seed_demo_events.py --reset
"""
from __future__ import annotations

import argparse
import json
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_EVENTS = PROJECT_DIR / "outputs" / "events.jsonl"
DEFAULT_CATALOG = PROJECT_DIR / "config" / "camera_catalog.json"


def read_camera_ids(catalog_path: Path) -> list[str]:
    try:
        payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    cameras = payload.get("cameras") if isinstance(payload, dict) else None
    if not isinstance(cameras, list):
        return []
    return [item["camera_id"] for item in cameras if isinstance(item, dict) and item.get("camera_id")]


def build_event(camera_id: str, observed_at: datetime, capacity: int, rng: random.Random) -> dict:
    person_count = rng.randint(0, capacity)
    chair_count = max(0, capacity - person_count + rng.randint(-3, 3))
    return {
        "schema_version": "vision.event.v1",
        "event_id": f"demo-{uuid.uuid4().hex[:12]}",
        "event_type": "occupancy_update",
        "observed_at": observed_at.isoformat(),
        "source": {"camera_id": camera_id, "stream": "demo://seed", "zone_id": None},
        "measurement": {
            "person_count": person_count,
            "chair_count": chair_count,
            "occupancy": person_count,
            "occupancy_rate": round(person_count / capacity, 4) if capacity else None,
            "zone_person_count": None,
            "zone_chair_count": None,
            "flow_crossings": 0,
        },
        "confidence": 0.35,
        "privacy": {"identity_mode": "anonymous", "face_recognition": False},
        "quality": {
            "stream_ok": True,
            "frame_width": 1920,
            "frame_height": 1080,
            "inference_seconds": round(rng.uniform(0.2, 0.6), 4),
            "cycle_seconds": round(rng.uniform(1.0, 1.8), 4),
        },
        "model": {"name": "demo-seed", "version": "0"},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo occupancy events")
    parser.add_argument("--camera", action="append", default=None,
                        help="camera_id (boleh diulang). Default: semua kamera di catalog")
    parser.add_argument("--count", type=int, default=6, help="jumlah event per kamera (default 6)")
    parser.add_argument("--capacity", type=int, default=20, help="kapasitas orang per kamera")
    parser.add_argument("--interval", type=int, default=60, help="jarak detik antar event")
    parser.add_argument("--events", type=Path, default=DEFAULT_EVENTS)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--reset", action="store_true", help="kosongkan event store lebih dulu")
    parser.add_argument("--seed", type=int, default=7, help="seed acak agar hasil dapat diulang")
    parser.add_argument("--watch", action="store_true",
                        help="terus tulis event baru tiap --interval detik sampai Ctrl+C")
    args = parser.parse_args()

    if args.count < 1:
        raise SystemExit("--count minimal 1")
    if args.capacity < 1:
        raise SystemExit("--capacity minimal 1")

    camera_ids = args.camera or read_camera_ids(args.catalog)
    if not camera_ids:
        raise SystemExit(
            f"Tidak ada camera_id. Isi {args.catalog} atau pakai --camera."
        )

    if args.reset and args.events.exists():
        args.events.unlink()

    rng = random.Random(args.seed)
    now = datetime.now(timezone.utc)
    args.events.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    with args.events.open("a", encoding="utf-8") as handle:
        for camera_id in camera_ids:
            for index in range(args.count):
                observed_at = now - timedelta(seconds=args.interval * (args.count - index - 1))
                event = build_event(camera_id, observed_at, args.capacity, rng)
                handle.write(json.dumps(event, ensure_ascii=False) + "\n")
                written += 1

    print(f"{written} event ditulis ke {args.events}")
    print(f"kamera: {', '.join(camera_ids)}")

    if not args.watch:
        return
    import time

    print(f"watch mode: event baru tiap {args.interval}s. Ctrl+C untuk berhenti.")
    try:
        with args.events.open("a", encoding="utf-8") as handle:
            while True:
                time.sleep(args.interval)
                for camera_id in camera_ids:
                    event = build_event(camera_id, datetime.now(timezone.utc), args.capacity, rng)
                    handle.write(json.dumps(event, ensure_ascii=False) + "\n")
                handle.flush()
                print(f"{len(camera_ids)} event baru ditulis", flush=True)
    except KeyboardInterrupt:
        print("watch dihentikan")


if __name__ == "__main__":
    main()
