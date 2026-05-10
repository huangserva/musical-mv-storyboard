#!/usr/bin/env python3
"""Export confirmed lip-sync proof clips from the final rendered video."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def seconds(value: Any, default: float | None = None) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def iter_clips_container(edl: Any) -> tuple[list[dict[str, Any]], str | None]:
    if isinstance(edl, list):
        return [item for item in edl if isinstance(item, dict)], None
    if isinstance(edl, dict):
        for key in ("clips", "timeline", "shots", "segments"):
            value = edl.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)], key
    return [], None


def clip_id(clip: dict[str, Any], index: int) -> str:
    return str(clip.get("id") or clip.get("shot_id") or clip.get("name") or f"clip_{index + 1}")


def clip_type(clip: dict[str, Any]) -> str:
    return str(clip.get("type") or clip.get("shot_type") or clip.get("role") or "")


def is_lipsync_clip(clip: dict[str, Any]) -> bool:
    return (
        clip_type(clip) == "lip_sync_closeup"
        or bool(clip.get("confirmed_variant"))
        or clip.get("lip_sync_offset_seconds") is not None
        or bool(clip.get("requires_exact_lip_sync"))
    )


def safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value).strip("_")


def run_ffmpeg(final_video: Path, start: float, duration: float, output: Path, crf: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            f"{start:.3f}",
            "-i",
            str(final_video),
            "-t",
            f"{duration:.3f}",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            crf,
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(output),
        ],
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("edl", type=Path, help="EDL JSON with confirmed lip-sync clips")
    parser.add_argument("--final-video", required=True, type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("lipsync_proof"))
    parser.add_argument("--pad-before", type=float, default=0.15)
    parser.add_argument("--pad-after", type=float, default=0.25)
    parser.add_argument("--crf", default="18")
    parser.add_argument("--update-edl", action="store_true", help="Write proof_path back into the EDL JSON")
    args = parser.parse_args()

    edl_path = args.edl.expanduser().resolve()
    final_video = args.final_video.expanduser().resolve()
    if not final_video.exists():
        raise SystemExit(f"final video not found: {final_video}")

    edl = load_json(edl_path)
    clips, container_key = iter_clips_container(edl)
    if not clips:
        raise SystemExit("EDL has no clips/timeline/shots/segments list")

    output_dir = args.output_dir.expanduser()
    if not output_dir.is_absolute():
        output_dir = edl_path.parent / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    exported: list[dict[str, Any]] = []
    for index, clip in enumerate(clips):
        if not is_lipsync_clip(clip) or clip.get("proof_required") is False:
            continue
        cid = clip_id(clip, index)
        start = seconds(clip.get("proof_start", clip.get("timeline_start", clip.get("start"))))
        end = seconds(clip.get("proof_end", clip.get("timeline_end", clip.get("end"))))
        duration = seconds(clip.get("proof_duration", clip.get("duration")))
        if start is None:
            raise SystemExit(f"{cid}: missing proof_start/timeline_start/start")
        if duration is None:
            if end is None:
                raise SystemExit(f"{cid}: missing proof_end/timeline_end/end or proof_duration/duration")
            duration = end - start
        proof_start = max(0.0, start - args.pad_before)
        proof_duration = duration + args.pad_before + args.pad_after
        output = output_dir / f"{safe_name(cid)}_final_lipsync_proof.mp4"
        run_ffmpeg(final_video, proof_start, proof_duration, output, args.crf)
        rel_path = os.path.relpath(output, edl_path.parent)
        clip["proof_path"] = rel_path
        clip["proof_start"] = round(proof_start, 3)
        clip["proof_duration"] = round(proof_duration, 3)
        exported.append({"clip_id": cid, "proof_path": rel_path, "start": proof_start, "duration": proof_duration})

    if args.update_edl:
        if isinstance(edl, list):
            edl_path.write_text(json.dumps(clips, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        elif isinstance(edl, dict) and container_key:
            edl[container_key] = clips
            edl_path.write_text(json.dumps(edl, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"exported": exported}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

