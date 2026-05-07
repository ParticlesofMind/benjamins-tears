#!/usr/bin/env python3
"""
Automate Benjamin's first-pass Mesh2Motion browser flow.

This drives the local Mesh2Motion create page with Playwright:
- upload a clean static GLB
- choose the Human skeleton
- use the single hand bone preset to avoid fragile finger cleanup
- bind the pose with Mesh2Motion defaults
- select a compact starter animation set
- download the rigged GLB to a project path

The result is an autopilot pass, not a final art sign-off. If the joints need
character-specific cleanup, rerun with --stop-at-joints and adjust them by hand.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOL_CACHE_DIR = Path.home() / "Library" / "Application Support" / "BenjaminTears"
APP_DIR = TOOL_CACHE_DIR / "mesh2motion-app"
DEFAULT_INPUT = PROJECT_ROOT / "assets/models/characters/benjamin/source/BenjaminCharacter_mesh2motion_upload.glb"
DEFAULT_OUTPUT = PROJECT_ROOT / "assets/models/characters/benjamin/source/BenjaminCharacter_mesh2motion_rigged.glb"
DEFAULT_ANIMATIONS = (
    "Rest Pose",
    "TPose",
    "Idle_Loop",
    "Idle Listening",
    "Idle_Talking_Loop",
    "Walk_Loop",
    "Jog_Fwd_Loop",
    "Sprint_Loop",
    "Jump_Start",
    "Jump_Loop",
    "Jump_Land",
    "Greeting",
    "Head Nod",
    "Yes",
    "Angry",
)


def log(message: str) -> None:
    print(f"[mesh2motion-auto] {message}", flush=True)


def run(command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    log("$ " + " ".join(command))
    return subprocess.run(command, cwd=cwd, text=True, check=True)


def page_is_up(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/create.html", timeout=1.5) as response:
            return response.status < 500
    except (OSError, urllib.error.URLError):
        return False


def wait_for_page(port: int, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if page_is_up(port):
            return
        time.sleep(0.5)
    raise RuntimeError(f"Mesh2Motion did not respond on port {port} after {timeout:.0f}s")


def ensure_mesh2motion_server(port: int, update_setup: bool) -> None:
    if page_is_up(port):
        log(f"Mesh2Motion is already running at http://127.0.0.1:{port}/create.html")
        return

    setup_script = PROJECT_ROOT / "tools" / "setup_mesh2motion.py"
    command = [sys.executable, str(setup_script)]
    if APP_DIR.exists() and not update_setup:
        command.extend(["--skip-app", "--skip-assets", "--no-install"])
    command.extend(["--launch", "--no-open", "--port", str(port)])
    run(command)
    wait_for_page(port)


def playwright_command(session: str) -> list[str]:
    if shutil.which("npx") is None:
        raise RuntimeError("npx is required to run Playwright automation, but it was not found on PATH")
    return [
        "npx",
        "--yes",
        "--package",
        "@playwright/cli",
        "playwright-cli",
        "--session",
        session,
    ]


def parse_animations(value: str | None) -> list[str]:
    if value is None:
        return list(DEFAULT_ANIMATIONS)
    return [item.strip() for item in value.split(",") if item.strip()]


def build_playwright_body(
    url: str,
    input_path: Path,
    output_path: Path,
    skeleton_label: str,
    hand_preset: str,
    animations: list[str],
    stop_at_joints: bool,
) -> str:
    return f"""
async (page) => {{
  const url = {json.dumps(url)};
  const inputPath = {json.dumps(str(input_path))};
  const outputPath = {json.dumps(str(output_path))};
  const skeletonLabel = {json.dumps(skeleton_label)};
  const handPreset = {json.dumps(hand_preset)};
  const requestedAnimations = {json.dumps(animations)};
  const stopAtJoints = {json.dumps(stop_at_joints)};

  const label = () => document.querySelector('#current-step-label')?.textContent ?? '';
  await page.goto(url, {{ waitUntil: 'domcontentloaded' }});
  await page.waitForSelector('#model-upload', {{ state: 'attached', timeout: 30000 }});
  await page.setInputFiles('#model-upload', inputPath);

  await page.waitForFunction(() => (
    document.querySelector('#current-step-label')?.textContent ?? ''
  ).includes('Load Skeleton'), null, {{ timeout: 120000 }});

  await page.locator('#auto-align-model-button').click();
  await page.locator('#skeleton-selection').selectOption({{ label: skeletonLabel }});
  await page.locator('#hand-skeleton-selection').selectOption(handPreset);
  await page.locator('#load-skeleton-button').click();

  await page.waitForFunction(() => (
    document.querySelector('#current-step-label')?.textContent ?? ''
  ).includes('Position Joints'), null, {{ timeout: 120000 }});

  if (stopAtJoints) {{
    return {{
      status: 'stopped-at-joints',
      currentStep: await page.evaluate(label),
      inputPath,
      outputPath,
      skeletonLabel,
      handPreset
    }};
  }}

  await page.locator('#action_bind_pose').click();
  await page.waitForFunction(() => (
    document.querySelector('#current-step-label')?.textContent ?? ''
  ).includes('Test animations'), null, {{ timeout: 180000 }});
  await page.waitForFunction(() => (
    document.querySelectorAll('#animations-items input[type=checkbox]').length > 0
  ), null, {{ timeout: 180000 }});

  const selection = await page.evaluate((names) => {{
    const requested = new Set(names);
    const requestedUnderscore = new Set(names.map((name) => name.replace(/ /g, '_')));
    const selected = [];

    const matches = (inputName, requestedName) => {{
      return (
        inputName === requestedName ||
        inputName.replace(/_/g, ' ') === requestedName ||
        inputName === requestedName.replace(/ /g, '_')
      );
    }};

    for (const input of document.querySelectorAll('#animations-items input[type=checkbox]')) {{
      const inputName = input.name;
      const shouldSelect =
        requested.has(inputName) ||
        requested.has(inputName.replace(/_/g, ' ')) ||
        requestedUnderscore.has(inputName);

      if (shouldSelect) {{
        input.checked = true;
        selected.push(inputName);
        input.dispatchEvent(new Event('change', {{ bubbles: true }}));
      }}
    }}

    document.querySelector('#animations-items')?.dispatchEvent(new MouseEvent('click', {{ bubbles: true }}));

    const missing = names.filter((name) => !selected.some((selectedName) => matches(selectedName, name)));
    const exportButton = document.querySelector('#export-button');
    if (exportButton && selected.length > 0) {{
      exportButton.disabled = false;
    }}

    return {{
      requested: names,
      selected,
      missing,
      count: document.querySelector('#animation-selection-count')?.textContent ?? '0',
      exportDisabled: exportButton?.disabled ?? true
    }};
  }}, requestedAnimations);

  if (selection.selected.length === 0) {{
    throw new Error('No requested animations were found in Mesh2Motion.');
  }}

  await page.waitForFunction(() => !document.querySelector('#export-button')?.disabled, null, {{ timeout: 10000 }});
  const downloadPromise = page.waitForEvent('download', {{ timeout: 180000 }});
  await page.locator('#export-button').click();
  const download = await downloadPromise;
  await download.saveAs(outputPath);

  return {{
    status: 'downloaded',
    currentStep: await page.evaluate(label),
    suggestedFilename: download.suggestedFilename(),
    inputPath,
    outputPath,
    skeletonLabel,
    handPreset,
    selection
  }};
}}
"""


def automate(args: argparse.Namespace) -> None:
    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    animations = parse_animations(args.animations)
    url = f"http://127.0.0.1:{args.port}/create.html"

    if not input_path.exists():
        raise FileNotFoundError(f"Input GLB does not exist: {input_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    ensure_mesh2motion_server(args.port, update_setup=args.setup)

    base = playwright_command(args.session)
    open_command = [*base, "open", url]
    if args.headed:
        open_command.append("--headed")
    run(open_command)

    body = build_playwright_body(
        url=url,
        input_path=input_path,
        output_path=output_path,
        skeleton_label=args.skeleton,
        hand_preset=args.hand_preset,
        animations=animations,
        stop_at_joints=args.stop_at_joints,
    )
    result = subprocess.run([*base, "run-code", body], text=True, capture_output=True)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="")
    if result.returncode != 0 or "### Error" in result.stdout:
        raise RuntimeError(f"Playwright automation failed with exit code {result.returncode}")

    if args.stop_at_joints:
        log("Stopped at Position Joints for manual cleanup.")
    else:
        log(f"Saved rigged Mesh2Motion GLB: {output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Automate Benjamin's Mesh2Motion rigging browser flow")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Static Mesh2Motion upload GLB")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Rigged Mesh2Motion GLB output path")
    parser.add_argument("--port", type=int, default=5173, help="Local Mesh2Motion dev server port")
    parser.add_argument("--session", default="mesh2motion-benjamin", help="Playwright session name")
    parser.add_argument("--skeleton", default="Human", help="Mesh2Motion skeleton label")
    parser.add_argument("--hand-preset", default="single-bone", help="Mesh2Motion human hand preset value")
    parser.add_argument("--animations", help="Comma-separated animation names to select")
    parser.add_argument("--setup", action="store_true", help="Clone/update/install Mesh2Motion before launch")
    parser.add_argument("--stop-at-joints", action="store_true", help="Upload/select skeleton, then stop for manual joint cleanup")
    parser.add_argument("--headless", dest="headed", action="store_false", help="Do not force a visible browser window")
    parser.set_defaults(headed=True)
    return parser.parse_args()


def main() -> int:
    try:
        automate(parse_args())
    except (FileNotFoundError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"[mesh2motion-auto] ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
