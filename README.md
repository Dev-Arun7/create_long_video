# Video Hour Looper (FFmpeg + Python)

Create a long video (e.g., **5 hours**, **10 hours**) by repeating a **single source video** without re-encoding (stream copy).  
This keeps **the same quality, resolution, codec, and audio** as the source, and shows **progress %** while working.

## Features

- ✅ Repeat a single source video to reach a target duration (hours)
- ✅ **No quality loss** (uses FFmpeg stream copy: `-c copy`)
- ✅ Output saved to the **same folder** as the source
- ✅ Output name: `final_video_{HOURS}_hours.mp4`
- ✅ Shows progress in `%` and `HH:MM:SS`

## How it works

1. Reads source duration using `ffprobe`
2. Computes how many repeats are needed for the target hours
3. Builds a concat list repeating the same file
4. Uses FFmpeg concat demuxer to join, and `-t` to trim to target duration
5. Prints progress based on FFmpeg `-progress pipe:1`

## Requirements

- Linux
- Python 3.8+
- FFmpeg installed (must include `ffmpeg` and `ffprobe`)

### Install FFmpeg

On Ubuntu/Debian:
```bash
sudo apt update
sudo apt install -y ffmpeg
```

On Fedora:
```bash
sudo dnf install -y ffmpeg
```

On Arch:
```bash
sudo pacman -S ffmpeg
```

## Usage

1. Clone the repo:
```bash
git clone <your-repo-url>
cd <your-repo-folder>
```

2. Edit the script variables in `video_hour_looper.py`:

```py
SOURCE_PATH = "/path/to/source.mp4"
TARGET_HOURS = 10
```

3. Run:
```bash
python3 video_hour_looper.py
```

Output will be created in the same folder as the source:
```
final_video_10_hours.mp4
```

## Output quality and resolution

This tool uses:
- `-c copy` (stream copy)

So:
- **No re-encoding**
- **No quality loss**
- **Same resolution**
- **Same audio** (repeats with the video)

### Small limitation (important)

Because it does stream copy, the final cut (trim to exact hours) may be off by a tiny amount if the cut point is not on a keyframe.  
For most looping videos, this is usually acceptable.

If you require frame-perfect exact duration, you’ll need a re-encode mode (not included yet).

## Troubleshooting

### 1) FFmpeg fails with timestamp / concat issues

Sometimes MP4 files have timestamp quirks. A quick fix is to **remux** the source once:

```bash
ffmpeg -i source.mp4 -c copy -movflags +faststart remuxed.mp4
```

Then set:
```py
SOURCE_PATH = "/path/to/remuxed.mp4"
```

### 2) “ffmpeg not found” / “ffprobe not found”

Install FFmpeg and ensure it’s in your PATH.

## Project structure

```
.
├── video_hour_looper.py
└── README.md
```

## Roadmap (optional ideas)

- CLI support (arguments: `--source`, `--hours`, `--overwrite`)
- Auto versioning output name (`_v2`, `_v3` if file exists)
- Exact-duration mode (re-encode option)
- Support input folder (auto pick + natural sorting)

## Contributing

PRs welcome!  
If you want to add CLI support or exact-duration mode, open an issue first describing the approach.

## License

Choose a license and add `LICENSE` file. Common options:
- MIT (simple and permissive)
- Apache-2.0 (permissive + patent protection)

MIT is a good default for small utilities.

## Credits

Built with Python + FFmpeg.
