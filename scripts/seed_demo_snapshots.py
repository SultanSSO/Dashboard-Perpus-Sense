#!/usr/bin/env python3
"""Buat snapshot placeholder untuk panel Live Monitoring.

Build dashboard-only tidak punya kamera, jadi endpoint
``/api/v1/cameras/<id>/snapshot`` akan kosong. Skrip ini menulis JPEG
placeholder ke ``outputs/latest_<camera_id>.jpg`` supaya panel live punya
gambar untuk ditampilkan saat mengembangkan UI.

Contoh:
    .venv/bin/python scripts/seed_demo_snapshots.py
    .venv/bin/python scripts/seed_demo_snapshots.py --camera 1.145-CH13
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw

PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_DIR / "outputs"
DEFAULT_CATALOG = PROJECT_DIR / "config" / "camera_catalog.json"

WIDTH, HEIGHT = 1280, 720


def safe_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def read_cameras(catalog_path: Path) -> list[dict]:
    try:
        payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    cameras = payload.get("cameras") if isinstance(payload, dict) else None
    if not isinstance(cameras, list):
        return []
    return [item for item in cameras if isinstance(item, dict) and item.get("camera_id")]


def render(camera_id: str, location: str) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), (18, 24, 38))
    draw = ImageDraw.Draw(image)

    # Grid tipis supaya terlihat seperti frame kamera, bukan gambar polos.
    for x in range(0, WIDTH, 80):
        draw.line([(x, 0), (x, HEIGHT)], fill=(28, 36, 54))
    for y in range(0, HEIGHT, 80):
        draw.line([(0, y), (WIDTH, y)], fill=(28, 36, 54))

    draw.rectangle([(24, 24), (WIDTH - 24, HEIGHT - 24)], outline=(70, 90, 120), width=2)
    draw.text((48, 48), "PLACEHOLDER SNAPSHOT", fill=(240, 200, 90))
    draw.text((48, 76), f"camera: {camera_id}", fill=(220, 230, 245))
    draw.text((48, 100), f"lokasi: {location}", fill=(160, 180, 205))
    draw.text((48, 124), datetime.now().strftime("dibuat: %Y-%m-%d %H:%M:%S"), fill=(160, 180, 205))
    draw.text((48, HEIGHT - 60), "Tidak ada kamera terpasang pada build dashboard-only",
              fill=(120, 140, 165))
    return image


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed placeholder camera snapshots")
    parser.add_argument("--camera", action="append", default=None, help="camera_id (boleh diulang)")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    cameras = read_cameras(args.catalog)
    if args.camera:
        wanted = set(args.camera)
        cameras = [item for item in cameras if item["camera_id"] in wanted]
    if not cameras:
        raise SystemExit(f"Tidak ada kamera. Isi {args.catalog} atau pakai --camera.")

    args.output.mkdir(parents=True, exist_ok=True)
    for camera in cameras:
        camera_id = camera["camera_id"]
        path = args.output / f"latest_{safe_id(camera_id)}.jpg"
        render(camera_id, str(camera.get("location") or "-")).save(path, "JPEG", quality=85)
        print(f"snapshot: {path}")


if __name__ == "__main__":
    main()
