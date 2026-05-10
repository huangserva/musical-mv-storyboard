#!/usr/bin/env python3
"""Smart shot classification based on audio data.

Uses vocal density, energy level, section type, and position in song
to classify each section into one of five shot types.

Input:  music_timeline.json (from build_music_timeline.py)
Output: shot_plan.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


# Shot type definitions with classification heuristics
SHOT_TYPES = {
    "lip_sync_closeup": {
        "description": "Face visible, stable, frontal. Wav2Lip candidate.",
        "ideal_conditions": "high vocal density + high energy + chorus/emotional peak",
    },
    "performance_medium": {
        "description": "Half-body, side angle, walking. Rough mouth OK.",
        "ideal_conditions": "medium-high vocal density + moderate energy",
    },
    "dance_or_group": {
        "description": "Choreography, crowd, ritual. No mouth sync.",
        "ideal_conditions": "high energy + low-medium vocal density + strong beats",
    },
    "mv_broll": {
        "description": "Symbolic visuals, atmosphere. No mouth sync.",
        "ideal_conditions": "low vocal density + any energy level",
    },
    "transition": {
        "description": "Short visual bridges between sections.",
        "ideal_conditions": "section boundaries, short duration",
    },
}


def classify_section(sec: dict, song_context: dict) -> str:
    """Classify a single section into a shot type.

    Uses multi-signal decision: vocal density, energy, section label,
    position in song, beat count, and lyric count.
    """
    vd = sec.get("vocal_density_norm", 0)   # 0-1 normalized
    en = sec.get("energy_norm", 0)           # 0-1 normalized
    label = sec.get("label", "verse")
    duration = sec.get("duration", 5)
    beat_count = len(sec.get("beats", []))
    lyric_count = len(sec.get("lyrics", []))
    position_ratio = sec.get("start", 0) / max(song_context.get("duration", 1), 1)

    # Score each shot type
    scores: dict[str, float] = {}

    # lip_sync_closeup: needs high vocal + high energy + face time
    scores["lip_sync_closeup"] = (
        vd * 0.40 +                    # vocal density is primary
        en * 0.25 +                     # energy boost
        (1.0 if label == "chorus" else 0.5 if label == "verse" else 0.1) * 0.20 +
        (1.0 if lyric_count > 2 else 0.3) * 0.15
    )

    # performance_medium: medium vocal, moderate energy
    scores["performance_medium"] = (
        min(vd, 0.8) * 0.30 +
        min(en, 0.8) * 0.25 +
        (1.0 if label == "verse" else 0.6 if label == "pre_chorus" else 0.2) * 0.25 +
        (1.0 if 0.3 < vd < 0.8 else 0.3) * 0.20
    )

    # dance_or_group: high energy + beats, vocal less important
    scores["dance_or_group"] = (
        en * 0.35 +
        (min(beat_count / max(duration * 2, 1), 1.0)) * 0.25 +
        (1.0 if label == "chorus" else 0.8 if label == "drop" else 0.3) * 0.20 +
        (1.0 if vd < 0.5 else 0.3) * 0.20
    )

    # mv_broll: low vocal, atmospheric
    scores["mv_broll"] = (
        (1.0 - vd) * 0.40 +
        (0.5 if 0.2 < en < 0.7 else 0.2) * 0.25 +
        (1.0 if label in ("intro", "bridge", "outro") else 0.3) * 0.20 +
        (1.0 if lyric_count < 2 else 0.2) * 0.15
    )

    # transition: short sections at boundaries
    scores["transition"] = (
        (1.0 if duration < 5 else 0.1) * 0.50 +
        (1.0 if label in ("intro", "outro", "drop") else 0.3) * 0.25 +
        (1.0 if position_ratio < 0.1 or position_ratio > 0.9 else 0.4) * 0.25
    )

    # Pick highest scoring type
    best = max(scores, key=scores.get)

    # Override rules:
    # 1. Very short sections (< 3s) are always transitions
    if duration < 3.0:
        return "transition"

    # 2. Intro/outro with no lyrics → broll
    if label in ("intro", "outro") and lyric_count == 0:
        return "mv_broll"

    # 3. Drop sections → dance (high energy, likely instrumental)
    if label == "drop":
        return "dance_or_group"

    return best


def requires_exact_lip_sync(shot_type: str, sec: dict) -> bool:
    """Determine if this shot needs exact Wav2Lip lip-sync."""
    if shot_type != "lip_sync_closeup":
        return False
    # Seedance-style lip-sync is only convincing in short windows.
    # Longer sections should be director-trimmed/split before being treated
    # as exact lip-sync anchors.
    if sec.get("duration", 0) > 5.0:
        return False
    # Only if vocal density is very high and it's a key section
    vd = sec.get("vocal_density", 0)
    label = sec.get("label", "")
    return vd > 0.6 and label in ("chorus", "verse")


def find_candidate_climax_windows(sec: dict, climax_analysis: dict | None) -> list[dict]:
    """Return top 4s climax windows that overlap a timeline section."""
    if not climax_analysis:
        return []
    start = sec.get("start", 0)
    end = sec.get("end", 0)
    candidates = []
    for item in climax_analysis.get("top_4s_windows", []):
        win_start = item.get("start", 0)
        win_end = item.get("end", 0)
        overlap = max(0.0, min(end, win_end) - max(start, win_start))
        if overlap > 0:
            candidate = dict(item)
            candidate["overlap"] = round(overlap, 2)
            candidates.append(candidate)
    return sorted(candidates, key=lambda x: (x.get("score", 0), x.get("overlap", 0)), reverse=True)[:3]


def normalize_lip_sync_fields(shots: list[dict]) -> None:
    """Keep lip-sync metadata consistent after budget downgrades."""
    for shot in shots:
        if shot["shot_type"] != "lip_sync_closeup":
            shot["requires_exact_lip_sync"] = False
            shot["target_lip_sync_duration"] = None
            shot["needs_director_lip_trim"] = False
            continue

        shot["target_lip_sync_duration"] = min(4.0, float(shot.get("duration", 4.0)))
        shot["needs_director_lip_trim"] = bool(shot.get("duration", 0) > 5.0)
        if shot["needs_director_lip_trim"]:
            shot["requires_exact_lip_sync"] = False


def classify_timeline(timeline: dict, climax_analysis: dict | None = None) -> dict:
    """Classify all sections in a timeline."""
    sections = timeline.get("sections", [])
    song_context = {
        "duration": timeline.get("duration", 0),
        "tempo_bpm": timeline.get("tempo_bpm", 0),
    }

    shots = []
    for sec in sections:
        shot_type = classify_section(sec, song_context)
        needs_lip = requires_exact_lip_sync(shot_type, sec)
        candidate_climax_windows = find_candidate_climax_windows(sec, climax_analysis)

        shots.append({
            "shot_id": f"shot_{len(shots) + 1:02d}",
            "section_id": sec.get("id", ""),
            "section": sec.get("label", ""),
            "start": sec["start"],
            "end": sec["end"],
            "duration": sec["duration"],
            "shot_type": shot_type,
            "requires_exact_lip_sync": needs_lip,
            "target_lip_sync_duration": 4.0 if shot_type == "lip_sync_closeup" else None,
            "needs_director_lip_trim": bool(shot_type == "lip_sync_closeup" and sec.get("duration", 0) > 5.0),
            "candidate_climax_windows": candidate_climax_windows,
            "music_reason": "",
            "climax_window": None,
            "vocal_density": sec.get("vocal_density", 0),
            "energy": sec.get("avg_energy", 0),
            "beat_count": len(sec.get("beats", [])),
            "lyric_count": len(sec.get("lyrics", [])),
            # Director fills these in (Step 4):
            "director_intent": "",
            "visual_description": "",
            "camera": "",
            "lighting": "",
            "reference_style": "",
            "lip_sync_notes": "",
            "seedance_image_prompt": "",
            "seedance_video_prompt": "",
        })

    # Enforce lip-sync budget: max 30% of total duration
    total_dur = sum(s["duration"] for s in shots)
    lip_dur = sum(s["duration"] for s in shots if s["shot_type"] == "lip_sync_closeup")
    if lip_dur > total_dur * 0.3:
        # Downgrade lowest-energy lip-sync shots to performance_medium
        lip_shots = sorted(
            [s for s in shots if s["shot_type"] == "lip_sync_closeup"],
            key=lambda s: s["energy"],
        )
        budget = total_dur * 0.3
        for shot in lip_shots:
            if lip_dur <= budget:
                break
            shot["shot_type"] = "performance_medium"
            shot["requires_exact_lip_sync"] = False
            lip_dur -= shot["duration"]

    # Enforce broll minimum: at least 15% of total duration
    broll_dur = sum(s["duration"] for s in shots if s["shot_type"] == "mv_broll")
    if broll_dur < total_dur * 0.15:
        # Find lowest-vocal performance_medium shots to upgrade
        candidates = sorted(
            [s for s in shots if s["shot_type"] == "performance_medium"],
            key=lambda s: s["vocal_density"],
        )
        needed = total_dur * 0.15 - broll_dur
        for shot in candidates:
            if needed <= 0:
                break
            shot["shot_type"] = "mv_broll"
            broll_dur += shot["duration"]
            needed -= shot["duration"]

    normalize_lip_sync_fields(shots)

    # Renumber shots
    for i, shot in enumerate(shots):
        shot["shot_id"] = f"shot_{i + 1:02d}"

    # Summary
    type_counts: dict[str, float] = {}
    for s in shots:
        type_counts[s["shot_type"]] = type_counts.get(s["shot_type"], 0) + s["duration"]

    return {
        "duration": timeline.get("duration", 0),
        "tempo_bpm": timeline.get("tempo_bpm", 0),
        "total_shots": len(shots),
        "shots": shots,
        "distribution": {k: round(v / total_dur * 100, 1) if total_dur > 0 else 0 for k, v in type_counts.items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify shots based on audio data")
    parser.add_argument("timeline", help="Path to music_timeline.json")
    parser.add_argument("--climax", help="Path to music_climax_analysis.json (optional)")
    parser.add_argument("--output", default="shot_plan.json", help="Output path")
    args = parser.parse_args()

    timeline_path = Path(args.timeline).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    if not timeline_path.exists():
        print(f"Error: {timeline_path} not found", file=sys.stderr)
        sys.exit(1)

    timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    climax_analysis = None
    if args.climax:
        climax_path = Path(args.climax).expanduser().resolve()
        if climax_path.exists():
            climax_analysis = json.loads(climax_path.read_text(encoding="utf-8"))
    shot_plan = classify_timeline(timeline, climax_analysis)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(shot_plan, ensure_ascii=False, indent=2), encoding="utf-8")

    # Summary
    print(f"Shot plan: {output_path}")
    print(f"  Total shots: {shot_plan['total_shots']}")
    print(f"  Distribution:")
    for stype, pct in sorted(shot_plan["distribution"].items(), key=lambda x: -x[1]):
        print(f"    {stype:<22s}: {pct:>5.1f}%")
    print()
    print("  Shots:")
    for shot in shot_plan["shots"]:
        lip_marker = " 🔴 lip-sync" if shot["requires_exact_lip_sync"] else ""
        print(f"    {shot['shot_id']}  [{shot['start']:>5.1f}-{shot['end']:>5.1f}s] "
              f"{shot['shot_type']:<22s} {shot['section']:<12s}{lip_marker}")


if __name__ == "__main__":
    main()
