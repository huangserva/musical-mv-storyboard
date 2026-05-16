#!/usr/bin/env python3
"""Validate that lip-sync shots are driven by clean vocal phrases."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_PHRASE_FIELDS = {
    "phrase_id",
    "lyric_text",
    "source_start",
    "source_end",
    "duration",
    "reference_audio_wav",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def resolve_path(path_value: str, base_dir: Path) -> Path:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return path


def iter_shots(shot_plan: Any) -> list[dict[str, Any]]:
    if isinstance(shot_plan, list):
        return [item for item in shot_plan if isinstance(item, dict)]
    if not isinstance(shot_plan, dict):
        return []
    for key in ("shots", "clips", "timeline", "segments"):
        value = shot_plan.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def is_lip_sync_shot(shot: dict[str, Any]) -> bool:
    shot_type = str(shot.get("shot_type") or shot.get("type") or "")
    return shot_type == "lip_sync_closeup" or bool(shot.get("requires_exact_lip_sync"))


def shot_id(shot: dict[str, Any], index: int) -> str:
    return str(shot.get("shot_id") or shot.get("id") or shot.get("name") or f"shot_{index + 1:02d}")


def validate_phrase_map(phrase_map: dict[str, Any], base_dir: Path, require_audio: bool) -> tuple[dict[str, dict[str, Any]], list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    phrases_raw = phrase_map.get("phrases")
    if not isinstance(phrases_raw, list) or not phrases_raw:
        return {}, ["phrase_map.phrases must be a non-empty list"], warnings

    phrases: dict[str, dict[str, Any]] = {}
    for index, phrase in enumerate(phrases_raw):
        if not isinstance(phrase, dict):
            errors.append(f"phrases[{index}] must be an object")
            continue

        pid = str(phrase.get("phrase_id") or "")
        if not pid:
            errors.append(f"phrases[{index}] missing phrase_id")
            continue
        if pid in phrases:
            errors.append(f"duplicate phrase_id: {pid}")
            continue
        phrases[pid] = phrase

        missing = sorted(REQUIRED_PHRASE_FIELDS - phrase.keys())
        if missing:
            errors.append(f"{pid}: missing required fields: {', '.join(missing)}")

        start = as_float(phrase.get("source_start"))
        end = as_float(phrase.get("source_end"))
        duration = as_float(phrase.get("duration"))
        if start is None or end is None or end <= start:
            errors.append(f"{pid}: source_start/source_end must define a positive range")
        if duration is None or duration <= 0:
            errors.append(f"{pid}: duration must be positive")
        if start is not None and end is not None and duration is not None and abs((end - start) - duration) > 0.15:
            warnings.append(f"{pid}: duration differs from source_end-source_start by {abs((end - start) - duration):.3f}s")

        audio = phrase.get("reference_audio_wav")
        if isinstance(audio, str) and audio:
            audio_path = resolve_path(audio, base_dir)
            if require_audio and not audio_path.exists():
                errors.append(f"{pid}: reference_audio_wav does not exist: {audio_path}")
        else:
            errors.append(f"{pid}: reference_audio_wav must be a path string")

        lyric = str(phrase.get("lyric_text") or "").strip()
        if not lyric:
            errors.append(f"{pid}: lyric_text must not be empty")

        timing = phrase.get("lyric_timing") or phrase.get("word_timing")
        if timing is None:
            warnings.append(f"{pid}: no lyric_timing/word_timing provided")
        elif not isinstance(timing, list) or not timing:
            errors.append(f"{pid}: lyric_timing/word_timing must be a non-empty list when present")
        else:
            previous_end = 0.0
            for t_index, item in enumerate(timing):
                if not isinstance(item, dict):
                    errors.append(f"{pid}: timing[{t_index}] must be an object")
                    continue
                t_start = as_float(item.get("start"))
                t_end = as_float(item.get("end"))
                text = str(item.get("text") or item.get("word") or "").strip()
                if t_start is None or t_end is None or t_end <= t_start:
                    errors.append(f"{pid}: timing[{t_index}] must define a positive range")
                    continue
                if duration is not None and t_end > duration + 0.15:
                    errors.append(f"{pid}: timing[{t_index}] ends after phrase duration")
                if t_start + 0.05 < previous_end:
                    warnings.append(f"{pid}: timing[{t_index}] overlaps previous timing item")
                if not text:
                    warnings.append(f"{pid}: timing[{t_index}] has no text")
                previous_end = max(previous_end, t_end)

    return phrases, errors, warnings


def validate_shot_plan(shot_plan: Any, phrases: dict[str, dict[str, Any]]) -> tuple[int, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    lip_count = 0
    for index, shot in enumerate(iter_shots(shot_plan)):
        if not is_lip_sync_shot(shot):
            continue
        lip_count += 1
        sid = shot_id(shot, index)
        phrase_id = str(shot.get("lip_sync_phrase_id") or shot.get("phrase_id") or "")
        if not phrase_id:
            errors.append(f"{sid}: lip-sync shot missing lip_sync_phrase_id")
            continue
        if phrase_id not in phrases:
            errors.append(f"{sid}: lip_sync_phrase_id not found in phrase map: {phrase_id}")
            continue
        if not shot.get("reference_audio_wav"):
            warnings.append(f"{sid}: no reference_audio_wav copied onto shot; should inherit from {phrase_id}")
    return lip_count, errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phrase_map", type=Path, help="lip_sync_phrase_map.json")
    parser.add_argument("--shot-plan", type=Path, help="Optional shot_plan.director.json to validate against the phrase map")
    parser.add_argument("--allow-missing-audio", action="store_true", help="Do not fail if reference_audio_wav files are not present")
    args = parser.parse_args()

    phrase_map_path = args.phrase_map.expanduser().resolve()
    phrase_map = load_json(phrase_map_path)
    if not isinstance(phrase_map, dict):
        print(json.dumps({"errors": ["phrase map root must be an object"]}, ensure_ascii=False, indent=2))
        return 1

    phrases, errors, warnings = validate_phrase_map(
        phrase_map,
        phrase_map_path.parent,
        require_audio=not args.allow_missing_audio,
    )

    lip_count = None
    if args.shot_plan:
        shot_plan_path = args.shot_plan.expanduser().resolve()
        shot_plan = load_json(shot_plan_path)
        lip_count, shot_errors, shot_warnings = validate_shot_plan(shot_plan, phrases)
        errors.extend(shot_errors)
        warnings.extend(shot_warnings)

    summary = {
        "phrase_map": str(phrase_map_path),
        "phrases": len(phrases),
        "lip_sync_shots": lip_count,
        "errors": errors,
        "warnings": warnings,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
