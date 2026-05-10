#!/usr/bin/env python3
"""Validate that a musical MV final edit preserves the master audio timeline."""

from __future__ import annotations

import argparse
import json
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


def iter_clips(edl: Any) -> list[dict[str, Any]]:
    if isinstance(edl, list):
        return [item for item in edl if isinstance(item, dict)]
    if not isinstance(edl, dict):
        return []
    for key in ("clips", "timeline", "shots", "segments", "edl"):
        value = edl.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def clip_id(clip: dict[str, Any], index: int) -> str:
    return str(clip.get("id") or clip.get("shot_id") or clip.get("shot") or clip.get("name") or f"clip_{index + 1}")


def clip_type(clip: dict[str, Any]) -> str:
    return str(clip.get("type") or clip.get("shot_type") or clip.get("role") or "")


def is_lipsync_clip(clip: dict[str, Any]) -> bool:
    ctype = clip_type(clip)
    note = str(clip.get("note") or "").lower()
    return (
        ctype == "lip_sync_closeup"
        or bool(clip.get("confirmed_variant"))
        or clip.get("lip_sync_offset_seconds") is not None
        or bool(clip.get("requires_exact_lip_sync"))
        or note.startswith("lip sync")
    )


def is_cover_clip(clip: dict[str, Any]) -> bool:
    ctype = clip_type(clip).lower()
    return ctype in {"cover", "title", "title_card", "opening_card"} or "cover_mode" in clip


def ffprobe_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    return float(payload["format"]["duration"])


def resolve_path(path_value: str, base_dir: Path) -> Path:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("edl", type=Path, help="EDL JSON with clips/timeline entries")
    parser.add_argument("--final-video", type=Path, help="Final rendered MP4 to duration-check")
    parser.add_argument("--duration-tolerance", type=float, default=0.35)
    parser.add_argument("--offset-tolerance", type=float, default=0.08)
    parser.add_argument("--require-proofs", action="store_true", help="Require proof_path for confirmed lip-sync clips")
    args = parser.parse_args()

    edl_path = args.edl.expanduser().resolve()
    edl = load_json(edl_path)
    clips = iter_clips(edl)
    errors: list[str] = []
    warnings: list[str] = []

    if not clips:
        errors.append("EDL has no clips/timeline/shots/segments list")

    max_end = 0.0
    lipsync_count = 0
    cover_count = 0

    for index, clip in enumerate(clips):
        cid = clip_id(clip, index)
        start = seconds(clip.get("timeline_start", clip.get("start")))
        end = seconds(clip.get("timeline_end", clip.get("end")))
        duration = seconds(clip.get("duration"))

        if start is None:
            errors.append(f"{cid}: missing timeline_start/start")
        if end is None and duration is None:
            errors.append(f"{cid}: missing timeline_end/end or duration")
        if start is not None and end is not None:
            if end <= start:
                errors.append(f"{cid}: timeline_end must be greater than timeline_start")
            max_end = max(max_end, end)
            if duration is not None and abs((end - start) - duration) > args.duration_tolerance:
                warnings.append(f"{cid}: duration differs from timeline range by {abs((end - start) - duration):.3f}s")
        elif start is not None and duration is not None:
            max_end = max(max_end, start + duration)

        if is_cover_clip(clip):
            cover_count += 1
            mode = str(clip.get("cover_mode") or clip.get("mode") or "").lower()
            if not mode:
                warnings.append(f"{cid}: cover/title clip has no cover_mode; prefer replace or explicit insert")
            elif mode == "insert" and not (clip.get("timeline_shift_ack") or isinstance(edl, dict) and edl.get("timeline_shift_ack")):
                errors.append(f"{cid}: cover_mode=insert without timeline_shift_ack; this can break lip-sync")

        if is_lipsync_clip(clip):
            lipsync_count += 1
            lyric_start = seconds(clip.get("lyric_start"))
            offset = seconds(clip.get("lip_sync_offset_seconds"))
            timeline_start = seconds(clip.get("timeline_start", clip.get("start")))
            if lyric_start is None:
                errors.append(f"{cid}: confirmed lip-sync missing lyric_start")
            if offset is None:
                errors.append(f"{cid}: confirmed lip-sync missing lip_sync_offset_seconds")
            if timeline_start is None:
                errors.append(f"{cid}: confirmed lip-sync missing timeline_start")
            if lyric_start is not None and offset is not None and timeline_start is not None:
                expected = lyric_start - offset
                delta = abs(timeline_start - expected)
                if delta > args.offset_tolerance:
                    errors.append(
                        f"{cid}: lip-sync offset broken; timeline_start={timeline_start:.3f}, "
                        f"expected={expected:.3f}, delta={delta:.3f}s"
                    )
            if args.require_proofs and clip.get("proof_required", True):
                proof_path = clip.get("proof_path")
                if not proof_path:
                    errors.append(f"{cid}: proof_required but proof_path missing")
                else:
                    resolved = resolve_path(str(proof_path), edl_path.parent)
                    if not resolved.exists():
                        errors.append(f"{cid}: proof_path does not exist: {resolved}")

    if args.final_video:
        final_video = args.final_video.expanduser().resolve()
        if not final_video.exists():
            errors.append(f"final video not found: {final_video}")
        else:
            try:
                final_duration = ffprobe_duration(final_video)
                declared_duration = seconds(edl.get("duration")) if isinstance(edl, dict) else None
                expected_duration = declared_duration or max_end
                if expected_duration and abs(final_duration - expected_duration) > args.duration_tolerance:
                    errors.append(
                        f"final duration mismatch: video={final_duration:.3f}s expected={expected_duration:.3f}s"
                    )
            except Exception as exc:  # pragma: no cover - subprocess/environment failure
                errors.append(f"ffprobe failed for final video: {exc}")

    summary = {
        "edl": str(edl_path),
        "clips": len(clips),
        "lip_sync_clips": lipsync_count,
        "cover_or_title_clips": cover_count,
        "timeline_end": round(max_end, 3),
        "errors": errors,
        "warnings": warnings,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
