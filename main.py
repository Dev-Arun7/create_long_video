#!/usr/bin/env python3
import os
import sys
import math
import shlex
import tempfile
import subprocess
from pathlib import Path
from shutil import disk_usage


# =========================
# USER VARIABLES (edit these)
# =========================
SOURCE_PATH = "/home/arun/Downloads/temp/215368.mp4"  # <-- set your source video file path
TARGET_HOURS = 2                # <-- e.g., 10, 5, etc.
TARGET_PATH = "/home/arun/Downloads/temp"
FASTSTART = False  # True = better for web streaming, adds rewrite time at end

# =========================
# Helpers
# =========================
def require_cmd(cmd: str) -> None:
    """Ensure a command exists in PATH."""
    if subprocess.call(["bash", "-lc", f"command -v {shlex.quote(cmd)} >/dev/null 2>&1"]) != 0:
        print(f"ERROR: '{cmd}' not found in PATH. Install it and try again.", file=sys.stderr)
        sys.exit(1)

def ffprobe_duration_seconds(src: str) -> float:
    """Return duration (seconds) using ffprobe."""
    # Uses format duration which is usually reliable for a single file
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        src
    ]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"ffprobe failed:\n{p.stderr.strip()}")
    val = p.stdout.strip()
    try:
        return float(val)
    except ValueError:
        raise RuntimeError(f"Could not parse duration from ffprobe output: {val!r}")

def hms(seconds: float) -> str:
    seconds = max(0, float(seconds))
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    # show seconds with 2 decimals to feel responsive
    return f"{h:02d}:{m:02d}:{s:05.2f}"

def estimate_output_size_bytes(src: str, src_seconds: float, target_seconds: float) -> int:
    src_size = os.path.getsize(src)  # bytes
    return int(src_size * (target_seconds / src_seconds))

def check_space_or_exit(output_dir: str, required_bytes: int, margin_pct: int = 10) -> None:
    free_bytes = disk_usage(output_dir).free
    needed = int(required_bytes * (1 + margin_pct / 100))

    print(f"Estimated output size: {required_bytes/1024/1024/1024:.2f} GB")
    print(f"Free space available: {free_bytes/1024/1024/1024:.2f} GB")
    print(f"Required (with {margin_pct}% margin): {needed/1024/1024/1024:.2f} GB")

    if free_bytes < needed:
        raise SystemExit("Not enough disk space. Free space or change output folder.")

def build_concat_list_file(src: str, repeats: int, list_path: str) -> None:
    """
    Build an ffmpeg concat demuxer list file.
    We use absolute paths and safe=0 in ffmpeg call.
    """
    src_abs = str(Path(src).resolve())
    with open(list_path, "w", encoding="utf-8") as f:
        for _ in range(repeats):
            # ffmpeg concat demuxer format
            f.write("file '{}'\n".format(src_abs.replace("'", "'\\''")))

def run_ffmpeg_with_progress(cmd, target_seconds: float) -> int:
    import time
    start_time = time.time()

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True
    )

    last_pct = -1.0
    try:
        for line in proc.stdout:
            line = line.strip()
            if line.startswith("out_time_ms="):
                try:
                    out_us = int(line.split("=", 1)[1])
                    out_sec = out_us / 1_000_000.0
                    pct = min(100.0, (out_sec / target_seconds) * 100.0) if target_seconds > 0 else 100.0
                    if pct - last_pct >= 0.5 or pct >= 100.0:
                        last_pct = pct
                        elapsed = time.time() - start_time
                        if pct > 0:
                            eta = (elapsed / pct) * (100.0 - pct)
                            eta_str = hms(eta)
                        else:
                            eta_str = "calculating..."
                        print(f"\rWorking... {pct:6.2f}%  ({hms(out_sec)} / {hms(target_seconds)})  |  Elapsed: {hms(elapsed)}  |  ETA: {eta_str}", end="", flush=True)
                except Exception:
                    pass

        rc = proc.wait()
        elapsed = time.time() - start_time
        print(f"\nTotal time taken: {hms(elapsed)}")
        if rc != 0:
            print(proc.stderr.read())
        return rc
    finally:
        if proc.stdout:
            proc.stdout.close()

# =========================
# Main
# =========================

def main():
    require_cmd("ffmpeg")
    require_cmd("ffprobe")

    src = SOURCE_PATH
    if not src or not os.path.isfile(src):
        print(f"ERROR: SOURCE_PATH does not exist or is not a file: {src}", file=sys.stderr)
        sys.exit(1)

    if TARGET_HOURS <= 0:
        print("ERROR: TARGET_HOURS must be > 0", file=sys.stderr)
        sys.exit(1)

    target_seconds = float(TARGET_HOURS) * 3600.0
    src_seconds = ffprobe_duration_seconds(src)

    if src_seconds <= 0:
        print("ERROR: Source duration seems invalid (<=0).", file=sys.stderr)
        sys.exit(1)

    repeats = int(math.ceil(target_seconds / src_seconds))

    # -----------------------------
    # create output folder if needed
    # -----------------------------
    os.makedirs(TARGET_PATH, exist_ok=True)  # <-- ADDED

    # -----------------------------
    # output file path
    # -----------------------------
    out_path = os.path.join(
        TARGET_PATH,
        f"final_video_{TARGET_HOURS}_hours.mp4"
    )  # <-- CHANGED to TARGET_PATH

    print(f"Source: {src}")
    print(f"Source duration: {hms(src_seconds)}")
    print(f"Target duration: {hms(target_seconds)}")
    print(f"Repeats needed: {repeats}")
    print(f"Output: {out_path}")
    print("Mode: stream copy (no re-encode) -> same quality/resolution/codec")

    required = estimate_output_size_bytes(src, src_seconds, target_seconds)

    # -----------------------------
    # check disk space in TARGET_PATH
    # -----------------------------
    check_space_or_exit(TARGET_PATH, required, margin_pct=10)  # <-- CHANGED

    # Create temporary concat list
    with tempfile.TemporaryDirectory() as td:
        list_file = os.path.join(td, "concat_list.txt")
        build_concat_list_file(src, repeats, list_file)

        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-f", "concat",
            "-safe", "0",
            "-i", list_file,
            "-t", str(target_seconds),
            "-c", "copy",
            *(["-movflags", "+faststart"] if FASTSTART else []),
            "-y",
            "-progress", "pipe:1",
            out_path
        ]

        rc = run_ffmpeg_with_progress(cmd, target_seconds)

        if rc != 0:
            print("ERROR: ffmpeg failed.")
            print("Try remuxing once:")
            print(f"  ffmpeg -i {shlex.quote(src)} -c copy -movflags +faststart remuxed.mp4")
            sys.exit(rc)

    print("Done ✅")

if __name__ == "__main__":
    main()


# ---------------------------
#        08-03-2026
#    Arun Balakrishnan
# ---------------------------