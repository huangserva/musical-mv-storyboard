#!/usr/bin/env python3
"""Audit an MV edit against lyrics, beats, climax windows, and visual source mapping."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def seconds(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def text(value: Any) -> str:
    return str(value or "").strip()


def iter_items(root: Any, keys: tuple[str, ...]) -> list[dict[str, Any]]:
    if isinstance(root, list):
        return [item for item in root if isinstance(item, dict)]
    if not isinstance(root, dict):
        return []
    for key in keys:
        value = root.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def iter_segments(edl: Any) -> list[dict[str, Any]]:
    return iter_items(edl, ("segments", "clips", "timeline", "shots", "edl"))


def iter_shots(shot_plan: Any) -> list[dict[str, Any]]:
    return iter_items(shot_plan, ("shots", "clips", "timeline", "segments"))


def item_id(item: dict[str, Any], index: int, prefix: str) -> str:
    return text(item.get("id") or item.get("shot_id") or item.get("shot") or item.get("unit_id") or item.get("name")) or f"{prefix}_{index + 1:02d}"


def time_range(item: dict[str, Any], start_keys: tuple[str, ...], end_keys: tuple[str, ...]) -> tuple[float | None, float | None]:
    start = None
    end = None
    for key in start_keys:
        start = seconds(item.get(key))
        if start is not None:
            break
    for key in end_keys:
        end = seconds(item.get(key))
        if end is not None:
            break
    duration = seconds(item.get("duration"))
    if start is not None and end is None and duration is not None:
        end = start + duration
    return start, end


def first_seconds(item: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    for key in keys:
        value = seconds(item.get(key))
        if value is not None:
            return value
    return None


def lyric_segments(audio_analysis: dict[str, Any]) -> list[dict[str, Any]]:
    raw = audio_analysis.get("whisper_segments") or audio_analysis.get("segments") or []
    rows: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        start = seconds(item.get("start"))
        end = seconds(item.get("end"))
        label = text(item.get("text") or item.get("lyric") or item.get("words"))
        if start is None or end is None or end <= start or not label:
            continue
        rows.append({"start": start, "end": end, "text": label})
    return rows


def beat_times(audio_analysis: dict[str, Any]) -> list[float]:
    beats: list[float] = []
    for item in audio_analysis.get("beat_map") or audio_analysis.get("beats") or []:
        if isinstance(item, (int, float)):
            value = float(item)
        elif isinstance(item, dict):
            value = seconds(item.get("time") or item.get("t") or item.get("start"))
            if value is None:
                continue
        else:
            continue
        if math.isfinite(value):
            beats.append(value)
    return sorted(beats)


def climax_windows(climax: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key in ("top_2s_windows", "top_4s_windows", "windows"):
        for item in climax.get(key) or []:
            if not isinstance(item, dict):
                continue
            start = seconds(item.get("start"))
            end = seconds(item.get("end"))
            if start is None or end is None or end <= start:
                continue
            rows.append(
                {
                    "type": key.replace("_windows", ""),
                    "start": start,
                    "end": end,
                    "score": seconds(item.get("score"), 0.0) or 0.0,
                    "energy": seconds(item.get("energy"), 0.0) or 0.0,
                    "onset": seconds(item.get("onset"), 0.0) or 0.0,
                }
            )
    return sorted(rows, key=lambda row: (row["start"], -(row["score"] or 0)))


def nearest_range(t: float, rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    best: tuple[float, dict[str, Any]] | None = None
    for row in rows:
        start = float(row["start"])
        end = float(row["end"])
        dist = 0.0 if start <= t <= end else min(abs(t - start), abs(t - end))
        if best is None or dist < best[0]:
            best = (dist, row)
    if best is None:
        return None
    result = dict(best[1])
    result["distance"] = round(best[0], 3)
    result["relation"] = "inside" if best[0] == 0 else "near"
    return result


def nearest_value(t: float, values: list[float]) -> dict[str, Any] | None:
    if not values:
        return None
    value = min(values, key=lambda candidate: abs(candidate - t))
    return {"time": round(value, 3), "distance": round(abs(value - t), 3)}


def build_shot_lookup(shot_plan: Any) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for index, shot in enumerate(iter_shots(shot_plan)):
        sid = item_id(shot, index, "shot")
        lookup[sid] = shot
    return lookup


def segment_rows(edl: Any, shot_lookup: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    cursor = 0.0
    for index, seg in enumerate(iter_segments(edl)):
        sid = item_id(seg, index, "segment")
        start, end = time_range(seg, ("timeline_start", "start", "timeline_in"), ("timeline_end", "end", "timeline_out"))
        if start is None:
            start = cursor
        if end is None:
            duration = seconds(seg.get("duration"))
            if duration is None:
                continue
            end = start + duration
        cursor = max(cursor, end)
        source_start = first_seconds(seg, ("source_start", "source_in"))
        source_end = first_seconds(seg, ("source_end", "source_out"))
        shot = shot_lookup.get(sid) or shot_lookup.get(text(seg.get("shot_id") or seg.get("shot"))) or {}
        rows.append(
            {
                "segment_id": sid,
                "timeline_start": round(start, 3),
                "timeline_end": round(end, 3),
                "duration": round(end - start, 3),
                "source": text(seg.get("source")),
                "source_start": round(source_start, 3) if source_start is not None else None,
                "source_end": round(source_end, 3) if source_end is not None else None,
                "role": text(seg.get("role") or shot.get("music_reason") or shot.get("director_intent")),
                "shot_type": text(shot.get("shot_type") or shot.get("type")),
            }
        )
    return rows


def cut_rows(segments: list[dict[str, Any]], lyrics: list[dict[str, Any]], beats: list[float], climaxes: list[dict[str, Any]], beat_tolerance: float) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, segment in enumerate(segments):
        t = float(segment["timeline_start"])
        lyric = nearest_range(t, lyrics)
        climax = nearest_range(t, climaxes)
        beat = nearest_value(t, beats)
        prev = segments[index - 1] if index > 0 else None
        source_jump = None
        if prev and prev.get("source") == segment.get("source") and prev.get("source_end") is not None and segment.get("source_start") is not None:
            source_jump = round(float(segment["source_start"]) - float(prev["source_end"]), 3)
        rows.append(
            {
                "time": round(t, 3),
                "segment_id": segment["segment_id"],
                "source_start": segment.get("source_start"),
                "nearest_lyric": lyric,
                "nearest_beat": beat,
                "nearest_climax": climax,
                "on_beat": bool(beat and beat["distance"] <= beat_tolerance),
                "source_jump": source_jump,
                "role": segment.get("role", ""),
            }
        )
    return rows


def findings(cuts: list[dict[str, Any]], segments: list[dict[str, Any]], lyrics: list[dict[str, Any]], climaxes: list[dict[str, Any]], beat_tolerance: float) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for cut in cuts:
        climax = cut.get("nearest_climax") or {}
        beat = cut.get("nearest_beat") or {}
        if climax and climax.get("distance", 99) <= 0.25 and not cut["on_beat"]:
            out.append(
                {
                    "priority": "P1",
                    "time": cut["time"],
                    "problem": "Cut is near a climax window but not close to a detected beat.",
                    "evidence": f"nearest beat distance={beat.get('distance')}, climax={climax.get('start')}-{climax.get('end')} score={climax.get('score')}",
                    "recommendation": "Move the visual cut to the nearest beat or explain the intentional off-beat cut in EDL role.",
                }
            )
    # Check whether strong late vocal/climax windows are covered by quiet return roles.
    for segment in segments:
        role = str(segment.get("role") or "").lower()
        quiet_role = any(token in role for token in ("return", "dawn", "quiet", "归位", "天亮", "复原", "收束"))
        if not quiet_role:
            continue
        start = float(segment["timeline_start"])
        end = float(segment["timeline_end"])
        strong = [
            row
            for row in climaxes
            if row.get("score", 0) >= 0.75 and max(start, row["start"]) < min(end, row["end"])
        ]
        vocal = [
            row
            for row in lyrics
            if max(start, row["start"]) < min(end, row["end"]) and len(row.get("text", "")) >= 4
        ]
        if strong and vocal:
            out.append(
                {
                    "priority": "P0",
                    "time": f"{start:.2f}-{end:.2f}",
                    "problem": "Quiet/return visual role overlaps strong vocal climax.",
                    "evidence": f"role={segment.get('role')}; vocal={vocal[0]['start']:.2f}-{vocal[0]['end']:.2f} {vocal[0]['text']}; climax_score={strong[0]['score']:.3f}",
                    "recommendation": "Keep performance/dance/lip-sync alive through the strong vocal window; compress return/dawn after the hook.",
                }
            )
    return out


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        f"# Rhythm Audit · {report.get('project', 'MV')}",
        "",
        f"- EDL: `{report['edl']}`",
        f"- Audio analysis: `{report['audio_analysis']}`",
        f"- Climax analysis: `{report['climax_analysis']}`",
        f"- Segments: {len(report['segments'])}",
        f"- Cuts: {len(report['cuts'])}",
        "",
        "## Findings",
        "",
    ]
    if not report["findings"]:
        lines.append("- No blocking rhythm findings detected by this audit.")
    for item in report["findings"]:
        lines.extend(
            [
                f"### {item['priority']} · {item['time']}",
                f"- Problem: {item['problem']}",
                f"- Evidence: {item['evidence']}",
                f"- Recommendation: {item['recommendation']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Segment Map",
            "",
            "| Segment | Timeline | Source | Role |",
            "|---|---:|---:|---|",
        ]
    )
    for row in report["segments"]:
        src = ""
        if row.get("source_start") is not None or row.get("source_end") is not None:
            src = f"{row.get('source_start')}-{row.get('source_end')}"
        lines.append(
            f"| {row['segment_id']} | {row['timeline_start']}-{row['timeline_end']} | {src} | {row.get('role', '')} |"
        )
    lines.extend(
        [
            "",
            "## Cut Alignment",
            "",
            "| Cut | Segment | Beat | Lyric | Climax | On beat |",
            "|---:|---|---:|---|---|---|",
        ]
    )
    for row in report["cuts"]:
        beat = row.get("nearest_beat") or {}
        lyric = row.get("nearest_lyric") or {}
        climax = row.get("nearest_climax") or {}
        lyric_text = f"{lyric.get('start')}-{lyric.get('end')} {lyric.get('text', '')} d={lyric.get('distance')}" if lyric else ""
        climax_text = f"{climax.get('start')}-{climax.get('end')} {climax.get('type')} score={climax.get('score')} d={climax.get('distance')}" if climax else ""
        lines.append(
            f"| {row['time']} | {row['segment_id']} | {beat.get('time', '')} d={beat.get('distance', '')} | {lyric_text} | {climax_text} | {row['on_beat']} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edl", required=True, type=Path, help="EDL JSON with segments/clips.")
    parser.add_argument("--audio-analysis", required=True, type=Path, help="audio_analysis.json from analyze_audio.py.")
    parser.add_argument("--climax", required=True, type=Path, help="music_climax_analysis.json from analyze_climax_windows.py.")
    parser.add_argument("--shot-plan", type=Path, help="Optional shot_plan/director plan for roles.")
    parser.add_argument("--project", default="", help="Project label for reports.")
    parser.add_argument("--output-json", type=Path, help="Write machine-readable audit JSON.")
    parser.add_argument("--output-md", type=Path, help="Write readable markdown audit.")
    parser.add_argument("--beat-tolerance", type=float, default=0.12, help="Max seconds from nearest beat to count as on-beat.")
    parser.add_argument("--fail-on-p0", action="store_true", help="Exit 1 if P0 findings are present.")
    args = parser.parse_args()

    edl_path = args.edl.expanduser().resolve()
    audio_path = args.audio_analysis.expanduser().resolve()
    climax_path = args.climax.expanduser().resolve()
    shot_path = args.shot_plan.expanduser().resolve() if args.shot_plan else None

    edl = load_json(edl_path)
    audio = load_json(audio_path)
    climax = load_json(climax_path)
    shot_plan = load_json(shot_path) if shot_path and shot_path.exists() else {}

    lyrics = lyric_segments(audio)
    beats = beat_times(audio)
    climaxes = climax_windows(climax)
    segments = segment_rows(edl, build_shot_lookup(shot_plan))
    cuts = cut_rows(segments, lyrics, beats, climaxes, args.beat_tolerance)
    found = findings(cuts, segments, lyrics, climaxes, args.beat_tolerance)

    report = {
        "project": args.project,
        "edl": str(edl_path),
        "audio_analysis": str(audio_path),
        "climax_analysis": str(climax_path),
        "shot_plan": str(shot_path) if shot_path else None,
        "beat_tolerance": args.beat_tolerance,
        "segments": segments,
        "cuts": cuts,
        "findings": found,
    }

    if args.output_json:
        out = args.output_json.expanduser().resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.output_md:
        out = args.output_md.expanduser().resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(markdown_report(report), encoding="utf-8")

    print(json.dumps({"findings": found, "segments": len(segments), "cuts": len(cuts)}, ensure_ascii=False, indent=2))
    if args.fail_on_p0 and any(item.get("priority") == "P0" for item in found):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
