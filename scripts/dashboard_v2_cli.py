#!/usr/bin/env python3
"""Jalankan Dashboard PerpusSense v2 (anti-slop).

Pemakaian:
    dashboard-perpus-v2                # host 127.0.0.1, port 4173
    dashboard-perpus-v2 --port 8080    # port lain
    dashboard-perpus-v2 --host 0.0.0.0 # akses dari perangkat lain di LAN

Skrip ini hanya pembungkus tipis: ia mengaktifkan venv proyek bila dipanggil
dari luar venv, lalu menyerahkan sisa argumen ke server dashboard yang sudah
ada. Tidak ada logika server yang diduplikasi di sini.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
UI_PATH = "/desain-awal-dashboard/login.html"


def _ensure_project_venv() -> None:
    """Pakai interpreter venv proyek bila skrip ini dijalankan dari luar venv."""
    venv_python = PROJECT_ROOT / ".venv" / "bin" / "python"
    if not venv_python.exists():
        return
    if Path(sys.executable).resolve() == venv_python.resolve():
        return
    if os.environ.get("PERPUS_V2_NO_REEXEC") == "1":
        return
    env = dict(os.environ, PERPUS_V2_NO_REEXEC="1")
    os.execve(str(venv_python), [str(venv_python), str(Path(__file__).resolve()), *sys.argv[1:]], env)


def main() -> int:
    _ensure_project_venv()

    parser = argparse.ArgumentParser(
        prog="dashboard-perpus-v2",
        description="Serve the PerpusSense v2 dashboard and CCTV API.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="alamat bind (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=4173, help="port HTTP (default 4173)")
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT, help="akar proyek")
    args = parser.parse_args()

    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    try:
        from vision_agent.dashboard.server import create_server
    except ModuleNotFoundError as exc:
        print(
            f"Gagal memuat server dashboard: {exc}\n"
            f"Pastikan dependency terpasang di venv proyek:\n"
            f"  {PROJECT_ROOT}/.venv/bin/python -m pip install -r requirements.txt",
            file=sys.stderr,
        )
        return 1

    root = args.root.resolve()
    server = create_server(root, args.host, args.port)
    print("PerpusSense Dashboard v2", flush=True)
    print(f"  UI  : http://{args.host}:{args.port}{UI_PATH}", flush=True)
    print(f"  API : http://{args.host}:{args.port}/api/v1/health", flush=True)
    print("  Stop: Ctrl+C", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nMenghentikan server.", flush=True)
    finally:
        server.runtime_manager.stop_all()  # type: ignore[attr-defined]
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
