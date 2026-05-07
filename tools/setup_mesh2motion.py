#!/usr/bin/env python3
"""
Set up local Mesh2Motion repos for the Benjamin Blender pipeline.

The upstream app is a Vite/TypeScript web app. This script keeps it in an
OS user-level tool cache, installs its npm dependencies, and can launch a local
dev server for use beside Blender. Keeping upstream checkouts outside the Godot
project prevents third-party optional integrations from polluting project scans.

Usage:
  python3 tools/setup_mesh2motion.py
  python3 tools/setup_mesh2motion.py --launch
  python3 tools/setup_mesh2motion.py --skip-assets --no-install
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import webbrowser
from pathlib import Path


TOOL_CACHE_DIR = Path.home() / "Library" / "Application Support" / "BenjaminTears"
APP_DIR = TOOL_CACHE_DIR / "mesh2motion-app"
ASSETS_DIR = TOOL_CACHE_DIR / "mesh2motion-assets"
APP_REPO = "https://github.com/Mesh2Motion/mesh2motion-app.git"
ASSETS_REPO = "https://github.com/Mesh2Motion/mesh2motion-assets.git"
PID_FILE = TOOL_CACHE_DIR / "mesh2motion-dev.pid"
LOG_FILE = TOOL_CACHE_DIR / "mesh2motion-dev.log"


def run(command: list[str], cwd: Path | None = None) -> None:
    print(f"[mesh2motion] $ {' '.join(command)}")
    subprocess.run(command, cwd=cwd, check=True)


def ensure_tool_cache() -> None:
    TOOL_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def clone_or_update(repo: str, target: Path) -> None:
    if (target / ".git").exists():
        run(["git", "pull", "--ff-only"], cwd=target)
        return
    if target.exists() and any(target.iterdir()):
        raise RuntimeError(f"{target} exists but is not a git checkout")
    run(["git", "clone", "--depth", "1", repo, str(target)])


def install_app_dependencies() -> None:
    if not APP_DIR.exists():
        raise RuntimeError(f"Mesh2Motion app is not cloned yet: {APP_DIR}")
    package_json = APP_DIR / "package.json"
    if not package_json.exists():
        raise RuntimeError(f"Missing package.json in {APP_DIR}")
    run(["npm", "install"], cwd=APP_DIR)


def process_is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def launch_app(port: int, open_browser: bool) -> None:
    if not APP_DIR.exists():
        raise RuntimeError(f"Mesh2Motion app is not cloned yet: {APP_DIR}")

    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text(encoding="utf-8").strip())
        except ValueError:
            pid = 0
        if pid and process_is_running(pid):
            url = f"http://127.0.0.1:{port}/create.html"
            print(f"[mesh2motion] Dev server already appears to be running: {url}")
            if open_browser:
                webbrowser.open(url)
            return

    LOG_FILE.parent.mkdir(exist_ok=True)
    log = LOG_FILE.open("a", encoding="utf-8")
    proc = subprocess.Popen(
        ["npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", str(port)],
        cwd=APP_DIR,
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    PID_FILE.write_text(str(proc.pid), encoding="utf-8")
    url = f"http://127.0.0.1:{port}/create.html"
    print(f"[mesh2motion] Started dev server PID {proc.pid}: {url}")
    print(f"[mesh2motion] Log: {LOG_FILE}")
    if open_browser:
        webbrowser.open(url)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Set up Mesh2Motion beside Blender")
    parser.add_argument("--skip-app", action="store_true", help="Do not clone/update mesh2motion-app")
    parser.add_argument("--skip-assets", action="store_true", help="Do not clone/update mesh2motion-assets")
    parser.add_argument("--no-install", action="store_true", help="Skip npm install for the app")
    parser.add_argument("--launch", action="store_true", help="Launch the local Vite dev server")
    parser.add_argument("--port", type=int, default=5173, help="Local Mesh2Motion dev server port")
    parser.add_argument("--no-open", action="store_true", help="Do not open the browser when launching")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ensure_tool_cache()

    try:
        if not args.skip_app:
            clone_or_update(APP_REPO, APP_DIR)
        if not args.skip_assets:
            clone_or_update(ASSETS_REPO, ASSETS_DIR)
        if not args.no_install and not args.skip_app:
            install_app_dependencies()
        if args.launch:
            launch_app(args.port, open_browser=not args.no_open)
    except (subprocess.CalledProcessError, RuntimeError) as exc:
        print(f"[mesh2motion] ERROR: {exc}", file=sys.stderr)
        return 1

    print("[mesh2motion] Ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
