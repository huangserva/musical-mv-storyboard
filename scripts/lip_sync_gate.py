#!/usr/bin/env python3
"""Hard gate for musical MV lip-sync planning and final proof integrity."""

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
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def resolve(path_value: str, base_dir: Path) -> Path:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return path


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


def iter_shots(plan: Any) -> list[dict[str, Any]]:
    return iter_items(plan, ("shots", "clips", "timeline", "segments"))


def iter_edl(edl: Any) -> list[dict[str, Any]]:
    return iter_items(edl, ("segments", "clips", "timeline", "shots", "edl"))


def first_seconds(item: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    for key in keys:
        value = seconds(item.get(key))
        if value is not None:
            return value
    return None


def item_id(item: dict[str, Any], index: int) -> str:
    return str(item.get("id") or item.get("shot_id") or item.get("shot") or item.get("name") or f"item_{index + 1:02d}")


def is_lip(item: dict[str, Any]) -> bool:
    shot_type = str(item.get("shot_type") or item.get("type") or "").lower()
    role = str(item.get("role") or item.get("note") or "").lower()
    return (
        shot_type == "lip_sync_closeup"
        or bool(item.get("requires_exact_lip_sync"))
        or item.get("lip_sync_phrase_id") is not None
        or item.get("phrase_id") is not None
        or item.get("lip_sync_offset_seconds") is not None
        or bool(item.get("confirmed_variant"))
        or role.startswith("lip sync")
    )


def phrase_index(phrase_map: dict[str, Any], base_dir: Path, require_audio: bool) -> tuple[dict[str, dict[str, Any]], list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    phrases: dict[str, dict[str, Any]] = {}
    raw = phrase_map.get("phrases")
    if not isinstance(raw, list) or not raw:
        return {}, ["phrase_map.phrases must be a non-empty list"], warnings
    for index, phrase in enumerate(raw):
        if not isinstance(phrase, dict):
            errors.append(f"phrases[{index}] must be an object")
            continue
        pid = str(phrase.get("phrase_id") or "")
        if not pid:
            errors.append(f"phrases[{index}] missing phrase_id")
            continue
        phrases[pid] = phrase
        start = seconds(phrase.get("source_start"))
        end = seconds(phrase.get("source_end"))
        duration = seconds(phrase.get("duration"))
        if start is None or end is None or end <= start:
            errors.append(f"{pid}: source_start/source_end must be a positive range")
        if duration is None or duration <= 0:
            errors.append(f"{pid}: duration must be positive")
        if duration is not None and duration > 5.5:
            warnings.append(f"{pid}: phrase duration {duration:.2f}s is long; prefer 3-5s lip-sync targets")
        if not str(phrase.get("lyric_text") or "").strip():
            errors.append(f"{pid}: lyric_text is required")
        audio = str(phrase.get("reference_audio_wav") or "")
        if not audio:
            errors.append(f"{pid}: reference_audio_wav is required")
        elif require_audio and not resolve(audio, base_dir).exists():
            errors.append(f"{pid}: reference_audio_wav missing: {resolve(audio, base_dir)}")
        timing = phrase.get("lyric_timing") or phrase.get("word_timing")
        if not timing:
            warnings.append(f"{pid}: lyric_timing/word_timing missing; exact prompt timing will be weak")
    return phrases, errors, warnings


def validate_shots(plan: Any, phrases: dict[str, dict[str, Any]]) -> tuple[int, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    count = 0
    for index, shot in enumerate(iter_shots(plan)):
        if not is_lip(shot):
            continue
        count += 1
        sid = item_id(shot, index)
        phrase_id = str(shot.get("lip_sync_phrase_id") or shot.get("phrase_id") or "")
        if not phrase_id:
            errors.append(f"{sid}: lip-sync shot missing lip_sync_phrase_id")
            continue
        if phrase_id not in phrases:
            errors.append(f"{sid}: phrase not found in lip_sync_phrase_map: {phrase_id}")
            continue
        target = seconds(shot.get("target_lip_sync_duration"))
        if target is None:
            warnings.append(f"{sid}: target_lip_sync_duration missing; default should be 3-4s")
        elif target > 5.0 and not shot.get("long_lip_sync_verified"):
            errors.append(f"{sid}: target_lip_sync_duration {target:.2f}s exceeds 5s without long_lip_sync_verified")
        if not (shot.get("reference_audio_wav") or phrases[phrase_id].get("reference_audio_wav")):
            errors.append(f"{sid}: no reference_audio_wav available from shot or phrase")
        prompt = str(shot.get("seedance_video_prompt") or shot.get("video_prompt") or "")
        if prompt and str(phrases[phrase_id].get("lyric_text") or "").strip() not in prompt:
            warnings.append(f"{sid}: video prompt does not visibly include exact phrase lyric_text")
    return count, errors, warnings


def validate_edl(edl: Any, require_proofs: bool, base_dir: Path) -> tuple[int, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    count = 0
    for index, clip in enumerate(iter_edl(edl)):
        if not is_lip(clip):
            continue
        count += 1
        cid = item_id(clip, index)
        if not clip.get("confirmed_variant"):
            errors.append(f"{cid}: confirmed lip-sync clip missing confirmed_variant")
        if seconds(clip.get("lyric_start")) is None:
            errors.append(f"{cid}: missing lyric_start")
        if seconds(clip.get("lip_sync_offset_seconds")) is None:
            errors.append(f"{cid}: missing lip_sync_offset_seconds")
        if first_seconds(clip, ("timeline_start", "start")) is None:
            errors.append(f"{cid}: missing timeline_start")
        if require_proofs and clip.get("proof_required", True):
            proof = str(clip.get("proof_path") or "")
            if not proof:
                errors.append(f"{cid}: proof_required but proof_path missing")
            elif not resolve(proof, base_dir).exists():
                errors.append(f"{cid}: proof_path missing: {resolve(proof, base_dir)}")
        if not clip.get("reference_audio_wav") and not clip.get("phrase_id") and not clip.get("lip_sync_phrase_id"):
            warnings.append(f"{cid}: no phrase/reference_audio recorded in EDL")
    return count, errors, warnings


def run_validate_audio_lock(edl: Path, final_video: Path | None, require_proofs: bool) -> tuple[list[str], list[str], dict[str, Any] | None]:
    script = Path(__file__).with_name("validate_audio_lock.py")
    cmd = [sys.executable, str(script), str(edl)]
    if final_video:
        cmd.extend(["--final-video", str(final_video)])
    if require_proofs:
        cmd.append("--require-proofs")
    result = subprocess.run(cmd, capture_output=True, text=True)
    payload = None
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        pass
    if result.returncode != 0:
        errors = payload.get("errors", []) if isinstance(payload, dict) else [result.stderr or result.stdout]
        warnings = payload.get("warnings", []) if isinstance(payload, dict) else []
        return errors, warnings, payload
    return [], payload.get("warnings", []) if isinstance(payload, dict) else [], payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phrase-map", type=Path, required=True, help="lip_sync_phrase_map.json")
    parser.add_argument("--shot-plan", type=Path, help="shot_plan.director.json")
    parser.add_argument("--edl", type=Path, help="Final/proof EDL JSON")
    parser.add_argument("--final-video", type=Path, help="Final rendered video for audio-lock check")
    parser.add_argument("--output", type=Path, help="Write gate report JSON")
    parser.add_argument("--mode", choices=["preflight", "final"], default="preflight")
    parser.add_argument("--allow-missing-audio", action="store_true")
    parser.add_argument("--require-proofs", action="store_true", help="Require proof_path for lip-sync EDL clips")
    args = parser.parse_args()

    phrase_path = args.phrase_map.expanduser().resolve()
    phrase_map = load_json(phrase_path)
    phrases, errors, warnings = phrase_index(phrase_map, phrase_path.parent, require_audio=not args.allow_missing_audio)

    shot_lip_count = None
    if args.shot_plan:
        shot_path = args.shot_plan.expanduser().resolve()
        count, shot_errors, shot_warnings = validate_shots(load_json(shot_path), phrases)
        shot_lip_count = count
        errors.extend(shot_errors)
        warnings.extend(shot_warnings)
    elif args.mode == "preflight":
        errors.append("--shot-plan is required in preflight mode")

    edl_lip_count = None
    audio_lock_report = None
    if args.edl:
        edl_path = args.edl.expanduser().resolve()
        count, edl_errors, edl_warnings = validate_edl(load_json(edl_path), args.require_proofs or args.mode == "final", edl_path.parent)
        edl_lip_count = count
        errors.extend(edl_errors)
        warnings.extend(edl_warnings)
        lock_errors, lock_warnings, audio_lock_report = run_validate_audio_lock(
            edl_path,
            args.final_video.expanduser().resolve() if args.final_video else None,
            args.require_proofs or args.mode == "final",
        )
        errors.extend(lock_errors)
        warnings.extend(lock_warnings)
    elif args.mode == "final":
        errors.append("--edl is required in final mode")

    report = {
        "mode": args.mode,
        "phrase_map": str(phrase_path),
        "phrases": len(phrases),
        "shot_lip_sync_count": shot_lip_count,
        "edl_lip_sync_count": edl_lip_count,
        "audio_lock_report": audio_lock_report,
        "errors": errors,
        "warnings": warnings,
        "passed": not errors,
    }

    if args.output:
        out = args.output.expanduser().resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
