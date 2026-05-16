#!/usr/bin/env python3
"""Validate music-to-visual duration planning before video prompts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def die(message: str) -> None:
    raise SystemExit(f"error: {message}")


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        die(f"file not found: {path}")
    except json.JSONDecodeError as exc:
        die(f"invalid JSON in {path}: {exc}")
    if not isinstance(data, dict):
        die("duration plan root must be an object")
    return data


def number(value: Any, field: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        die(f"{field} must be numeric")


def validate_unit(unit: dict[str, Any], index: int) -> dict[str, Any]:
    unit_id = str(unit.get("unit_id") or "")
    if not unit_id:
        die(f"generation_units[{index}] missing unit_id")

    start = number(unit.get("music_start"), f"{unit_id}.music_start")
    end = number(unit.get("music_end"), f"{unit_id}.music_end")
    if end <= start:
        die(f"{unit_id}.music_end must be greater than music_start")

    expected_duration = round(end - start, 3)
    final_duration = number(unit.get("final_duration"), f"{unit_id}.final_duration")
    seedance_duration = number(unit.get("seedance_duration"), f"{unit_id}.seedance_duration")
    max_major_actions = int(number(unit.get("max_major_actions", 1), f"{unit_id}.max_major_actions"))

    if abs(final_duration - expected_duration) > 0.08:
        die(
            f"{unit_id}.final_duration {final_duration} does not match "
            f"music_end-start {expected_duration}"
        )
    if seedance_duration < 5:
        die(f"{unit_id}.seedance_duration must be >= 5")
    if seedance_duration > 15:
        die(f"{unit_id}.seedance_duration must be <= 15")
    if seedance_duration + 0.1 < final_duration:
        die(f"{unit_id}.seedance_duration is shorter than final_duration")
    if max_major_actions > 2:
        die(f"{unit_id}.max_major_actions must be <= 2 for Seedance reliability")
    if not unit.get("primary_visual_action"):
        die(f"{unit_id} missing primary_visual_action")
    if not unit.get("prompt_strategy"):
        die(f"{unit_id} missing prompt_strategy")

    return {
        "unit_id": unit_id,
        "music_range": [start, end],
        "final_duration": round(final_duration, 3),
        "seedance_duration": seedance_duration,
        "max_major_actions": max_major_actions,
    }


def validate_plan(plan: dict[str, Any]) -> dict[str, Any]:
    units = plan.get("generation_units")
    if not isinstance(units, list) or not units:
        die("generation_units must be a non-empty list")

    checked_units = [
        validate_unit(unit, index)
        for index, unit in enumerate(units)
        if isinstance(unit, dict)
    ]
    if len(checked_units) != len(units):
        die("each generation unit must be an object")

    summary = plan.get("decision_summary") or {}
    window = summary.get("recommended_final_window") or {}
    start = window.get("start")
    end = window.get("end")
    if start is not None and end is not None:
        window_start = number(start, "recommended_final_window.start")
        window_end = number(end, "recommended_final_window.end")
        first = min(item["music_range"][0] for item in checked_units)
        last = max(item["music_range"][1] for item in checked_units)
        if first < window_start - 0.08 or last > window_end + 0.08:
            die("generation units extend outside recommended_final_window")

    report = {
        "status": "ok",
        "plan_id": plan.get("plan_id", ""),
        "unit_count": len(checked_units),
        "total_final_duration": round(sum(item["final_duration"] for item in checked_units), 3),
        "units": checked_units,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate visual duration plan JSON")
    parser.add_argument("plan", help="Path to visual_duration_plan.json")
    parser.add_argument("--output", help="Write validation report JSON")
    args = parser.parse_args()

    report = validate_plan(read_json(Path(args.plan).expanduser().resolve()))
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).expanduser().resolve().write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
