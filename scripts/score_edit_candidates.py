#!/usr/bin/env python3
"""Score MV edit candidates with a repeatable weighted rubric."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


DEFAULT_WEIGHTS = {
    "music_alignment": 0.25,
    "story_completeness": 0.20,
    "handoff_energy": 0.20,
    "visual_continuity": 0.15,
    "bug_maskability": 0.10,
    "editability": 0.10,
}


def die(message: str) -> None:
    raise SystemExit(f"error: {message}")


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        die(f"file not found: {path}")
    except json.JSONDecodeError as exc:
        die(f"invalid JSON in {path}: {exc}")
    if not isinstance(data, dict):
        die("scorecard root must be an object")
    return data


def normalize_weights(raw: Any) -> dict[str, float]:
    if raw is None:
        raw = DEFAULT_WEIGHTS
    if not isinstance(raw, dict) or not raw:
        die("weights must be a non-empty object")

    weights: dict[str, float] = {}
    for key, value in raw.items():
        try:
            weight = float(value)
        except (TypeError, ValueError):
            die(f"weight for {key!r} must be numeric")
        if weight < 0:
            die(f"weight for {key!r} must be >= 0")
        weights[str(key)] = weight

    if sum(weights.values()) <= 0:
        die("sum of weights must be > 0")
    return weights


def candidate_id(candidate: dict[str, Any], index: int) -> str:
    value = candidate.get("candidate_id") or candidate.get("id")
    if not value:
        die(f"candidate #{index + 1} missing candidate_id")
    return str(value)


def score_candidate(
    candidate: dict[str, Any],
    weights: dict[str, float],
    index: int,
) -> dict[str, Any]:
    cid = candidate_id(candidate, index)
    scores = candidate.get("scores")
    if not isinstance(scores, dict):
        die(f"candidate {cid!r} missing scores object")

    missing = [criterion for criterion in weights if criterion not in scores]
    if missing:
        die(f"candidate {cid!r} missing score(s): {', '.join(missing)}")

    weighted_total = 0.0
    for criterion, weight in weights.items():
        try:
            value = float(scores[criterion])
        except (TypeError, ValueError):
            die(f"candidate {cid!r} score {criterion!r} must be numeric")
        if value < 0 or value > 10:
            die(f"candidate {cid!r} score {criterion!r} must be 0-10")
        weighted_total += value * weight

    weighted_total /= sum(weights.values())
    blocking_issues = candidate.get("blocking_issues") or []
    if not isinstance(blocking_issues, list):
        die(f"candidate {cid!r} blocking_issues must be a list")

    return {
        "candidate_id": cid,
        "weighted_total": round(weighted_total, 3),
        "blocked": bool(blocking_issues),
        "blocking_issues": blocking_issues,
        "video": candidate.get("video", ""),
        "source_range": [candidate.get("source_in"), candidate.get("source_out")],
        "timeline_range": [candidate.get("timeline_in"), candidate.get("timeline_out")],
        "reasoning": candidate.get("reasoning", ""),
    }


def score_card(card: dict[str, Any]) -> dict[str, Any]:
    weights = normalize_weights(card.get("weights"))
    candidates = card.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        die("candidates must be a non-empty list")

    ranking = [
        score_candidate(candidate, weights, index)
        for index, candidate in enumerate(candidates)
    ]
    ranking.sort(key=lambda item: (item["blocked"], -item["weighted_total"]))

    recommended = next((item for item in ranking if not item["blocked"]), None)

    card["weights"] = weights
    card["ranking"] = ranking
    card["recommended_candidate"] = (
        recommended["candidate_id"] if recommended else ""
    )
    card["recommendation_status"] = "ok" if recommended else "all_candidates_blocked"
    card["scoring_policy"] = (
        "Recommend the highest weighted non-blocked candidate. Do not optimize only "
        "for one visual defect; music alignment, story completeness and handoff "
        "energy usually outrank a mild maskable bug."
    )
    return card


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Rank edit candidates with the musical MV edit-decision rubric."
    )
    parser.add_argument("scorecard", help="Path to edit_decision_qc.json")
    parser.add_argument("--output", help="Write scored JSON to this path")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Overwrite the input scorecard with computed ranking",
    )
    args = parser.parse_args()

    input_path = Path(args.scorecard)
    card = score_card(load_json(input_path))
    rendered = json.dumps(card, ensure_ascii=False, indent=2) + "\n"

    if args.write and args.output:
        die("--write and --output are mutually exclusive")
    if args.write:
        input_path.write_text(rendered, encoding="utf-8")
    elif args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
