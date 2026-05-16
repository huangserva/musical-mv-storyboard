#!/usr/bin/env python3
"""Gate final MV edits against edit-decision scorecards.

This script makes the edit decision enforceable:
- every scorecard must have a valid recommended_candidate
- blocked candidates cannot be recommended
- when an EDL is provided, the shot entry must reference the recommended candidate
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from score_edit_candidates import score_card


SOURCE_FIELDS = (
    "edit_decision_candidate_id",
    "selected_candidate_id",
    "candidate_id",
    "recommended_candidate",
    "source",
    "video",
    "file",
    "path",
    "source_video",
    "selected_video",
    "clip",
)


def die(message: str) -> None:
    raise SystemExit(f"error: {message}")


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        die(f"file not found: {path}")
    except json.JSONDecodeError as exc:
        die(f"invalid JSON in {path}: {exc}")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_id(value: Any) -> str:
    return "".join(ch for ch in str(value or "").lower() if ch.isalnum())


def path_tokens(value: Any, base_dir: Path | None = None) -> set[str]:
    if not value:
        return set()
    raw = str(value)
    tokens = {raw, Path(raw).name}
    path = Path(raw).expanduser()
    if base_dir and not path.is_absolute():
        path = base_dir / path
    try:
        tokens.add(str(path.resolve()))
    except OSError:
        tokens.add(str(path.absolute()))
    return {token for token in tokens if token}


def values_match(left: Any, right: Any, right_base_dir: Path | None = None) -> bool:
    if not left or not right:
        return False
    return bool(path_tokens(left) & path_tokens(right, right_base_dir))


def find_scorecards(explicit: list[str], discover_root: str | None) -> list[Path]:
    paths = [Path(item).expanduser().resolve() for item in explicit]
    if discover_root:
        root = Path(discover_root).expanduser().resolve()
        if not root.exists():
            die(f"discover root not found: {root}")
        paths.extend(sorted(root.rglob("*edit_decision_qc.json")))

    unique: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        if path not in seen:
            unique.append(path)
            seen.add(path)
    if not unique:
        die("no edit decision scorecards provided")
    return unique


def candidate_id(candidate: dict[str, Any]) -> str:
    return str(candidate.get("candidate_id") or candidate.get("id") or "")


def load_scorecard(path: Path) -> dict[str, Any]:
    raw = read_json(path)
    if not isinstance(raw, dict):
        die(f"scorecard root must be an object: {path}")
    scored = score_card(raw)

    recommended_id = str(scored.get("recommended_candidate") or "")
    if not recommended_id:
        die(f"scorecard has no recommended_candidate: {path}")

    candidates = scored.get("candidates") or []
    candidate = next(
        (item for item in candidates if candidate_id(item) == recommended_id),
        None,
    )
    if not isinstance(candidate, dict):
        die(f"recommended_candidate not found in candidates: {path}")
    if candidate.get("blocking_issues"):
        die(f"recommended_candidate is blocked: {recommended_id} in {path}")

    ranking = scored.get("ranking") or []
    ranked = next(
        (item for item in ranking if item.get("candidate_id") == recommended_id),
        {},
    )

    return {
        "path": path,
        "scorecard": scored,
        "shot_id": str(scored.get("shot_id") or scored.get("decision_id") or ""),
        "recommended_candidate": recommended_id,
        "recommended_video": candidate.get("video", ""),
        "recommended_score": ranked.get("weighted_total"),
        "candidate_count": len(candidates),
        "candidates": candidates,
    }


def extract_edl_entries(edl: Any) -> list[dict[str, Any]]:
    if isinstance(edl, list):
        return [item for item in edl if isinstance(item, dict)]
    if not isinstance(edl, dict):
        die("EDL must be an object or list")
    for key in ("clips", "segments", "edl", "timeline", "items"):
        value = edl.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    die("EDL does not contain clips/segments/edl/timeline/items list")


def entry_shot_id(entry: dict[str, Any]) -> str:
    return str(
        entry.get("shot_id")
        or entry.get("shot")
        or entry.get("id")
        or entry.get("name")
        or ""
    )


def entry_matches_shot(entry: dict[str, Any], shot_id: str) -> bool:
    raw_left = entry_shot_id(entry)
    raw_right = str(shot_id or "")
    left = normalize_id(raw_left)
    right = normalize_id(raw_right)
    if not left or not right:
        return False
    if left == right:
        return True

    # Common versioned clip names like shot_09_v2 or shot_09_trim are still
    # the same shot. Handoff names like shot_09_to_10_flash are not.
    normalized_raw_left = raw_left.lower().replace("-", "_")
    normalized_raw_right = raw_right.lower().replace("-", "_")
    prefix = f"{normalized_raw_right}_"
    if normalized_raw_left.startswith(prefix):
        suffix = normalized_raw_left[len(prefix):]
        return suffix.startswith(("v", "trim", "part", "candidate", "take"))
    return False


def entry_candidate_value(entry: dict[str, Any]) -> str:
    for key in (
        "edit_decision_candidate_id",
        "selected_candidate_id",
        "candidate_id",
        "recommended_candidate",
    ):
        if entry.get(key):
            return str(entry[key])
    return ""


def entry_source_values(entry: dict[str, Any]) -> list[Any]:
    values = []
    for key in SOURCE_FIELDS:
        if key in entry and entry[key]:
            values.append(entry[key])
    return values


def validate_edl(scorecards: list[dict[str, Any]], edl_path: Path) -> dict[str, Any]:
    edl = read_json(edl_path)
    entries = extract_edl_entries(edl)
    errors: list[str] = []
    checks: list[dict[str, Any]] = []

    for item in scorecards:
        shot_id = item["shot_id"]
        matches = [entry for entry in entries if entry_matches_shot(entry, shot_id)]
        if not matches:
            errors.append(f"EDL missing entry for {shot_id}")
            continue

        recommended_id = item["recommended_candidate"]
        recommended_video = item["recommended_video"]
        other_candidates = [
            candidate
            for candidate in item["candidates"]
            if candidate_id(candidate) and candidate_id(candidate) != recommended_id
        ]

        for entry in matches:
            explicit_candidate = entry_candidate_value(entry)
            source_values = entry_source_values(entry)
            scorecard_dir = item["path"].parent
            explicit_ok = explicit_candidate == recommended_id if explicit_candidate else False
            source_ok = any(
                values_match(value, recommended_video, scorecard_dir)
                for value in source_values
            )
            wrong_matches = [
                candidate_id(candidate)
                for candidate in other_candidates
                if any(
                    values_match(value, candidate.get("video", ""), scorecard_dir)
                    for value in source_values
                )
            ]

            check = {
                "shot_id": shot_id,
                "edl_entry_id": entry_shot_id(entry),
                "recommended_candidate": recommended_id,
                "explicit_candidate": explicit_candidate,
                "source_match": source_ok,
                "wrong_candidate_matches": wrong_matches,
            }
            checks.append(check)

            if explicit_candidate and not explicit_ok:
                errors.append(
                    f"{shot_id} EDL candidate {explicit_candidate!r} != recommended {recommended_id!r}"
                )
            elif wrong_matches and not source_ok:
                errors.append(
                    f"{shot_id} EDL references non-recommended candidate(s): {', '.join(wrong_matches)}"
                )
            elif not explicit_ok and not source_ok:
                errors.append(
                    f"{shot_id} EDL does not prove recommended candidate {recommended_id!r}; "
                    "add edit_decision_candidate_id or source the recommended video"
                )

    return {
        "path": str(edl_path),
        "entry_count": len(entries),
        "checks": checks,
        "errors": errors,
    }


def build_report(
    scorecard_paths: list[Path],
    edl_path: Path | None,
    require_edl: bool,
) -> dict[str, Any]:
    scorecards = [load_scorecard(path) for path in scorecard_paths]
    report: dict[str, Any] = {
        "status": "ok",
        "scorecards": [
            {
                "path": str(item["path"]),
                "shot_id": item["shot_id"],
                "recommended_candidate": item["recommended_candidate"],
                "recommended_video": item["recommended_video"],
                "recommended_score": item["recommended_score"],
                "candidate_count": item["candidate_count"],
            }
            for item in scorecards
        ],
        "edl": None,
        "errors": [],
    }

    if edl_path:
        edl_report = validate_edl(scorecards, edl_path)
        report["edl"] = edl_report
        report["errors"].extend(edl_report["errors"])
    elif require_edl:
        report["errors"].append("--require-edl set but no --edl provided")

    if report["errors"]:
        report["status"] = "failed"
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate final edit selections against edit-decision scorecards."
    )
    parser.add_argument(
        "--edit-decision-qc",
        action="append",
        default=[],
        help="Path to an edit_decision_qc.json file. Repeatable.",
    )
    parser.add_argument(
        "--discover-root",
        help="Find **/*edit_decision_qc.json under this project root.",
    )
    parser.add_argument("--edl", help="Final EDL JSON to validate against recommendations.")
    parser.add_argument("--output", help="Write final edit gate report JSON.")
    parser.add_argument("--require-edl", action="store_true", help="Fail if --edl is absent.")
    args = parser.parse_args()

    scorecard_paths = find_scorecards(args.edit_decision_qc, args.discover_root)
    edl_path = Path(args.edl).expanduser().resolve() if args.edl else None
    report = build_report(scorecard_paths, edl_path, args.require_edl)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"

    if args.output:
        write_json(Path(args.output).expanduser().resolve(), report)
    else:
        sys.stdout.write(rendered)

    if report["status"] != "ok":
        if args.output:
            sys.stderr.write(rendered)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
