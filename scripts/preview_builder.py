#!/usr/bin/env python3
"""Auto-discover project files and generate preview.html via build_preview.py."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def latest(root: Path, patterns: list[str]) -> Path | None:
    candidates: list[Path] = []
    for pattern in patterns:
        candidates.extend(path for path in root.rglob(pattern) if path.is_file())
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def prefer(root: Path, paths: list[str], patterns: list[str]) -> Path | None:
    for value in paths:
        path = root / value
        if path.exists():
            return path
    return latest(root, patterns)


def add_path(cmd: list[str], flag: str, path: Path | None) -> None:
    if path and path.exists():
        cmd.extend([flag, str(path)])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", type=Path, help="MV project root")
    parser.add_argument("--output", type=Path, help="Output preview.html; defaults to project_root/previews/preview.html")
    parser.add_argument("--style", default="", help="Project style label")
    parser.add_argument("--shot-plan", type=Path)
    parser.add_argument("--prompts", type=Path)
    parser.add_argument("--climax", type=Path)
    parser.add_argument("--director-score", type=Path)
    parser.add_argument("--final-video", type=Path)
    parser.add_argument("--focus-video", type=Path)
    parser.add_argument("--contact-sheet", type=Path)
    parser.add_argument("--edl", type=Path)
    parser.add_argument("--edit-decision-qc", type=Path)
    parser.add_argument("--dry-run", action="store_true", help="Print the resolved build_preview.py command without running it")
    args = parser.parse_args()

    root = args.project_root.expanduser().resolve()
    if not root.exists():
        print(f"project root not found: {root}", file=sys.stderr)
        return 1

    shot_plan = args.shot_plan or prefer(
        root,
        [
            "planning/shot_plan.director.json",
            "planning/shot_plan_v4.director.json",
            "shot_plan.director.json",
        ],
        ["*shot_plan*.director.json", "*shot_plan*.json"],
    )
    if not shot_plan or not shot_plan.exists():
        print("No shot plan found. Pass --shot-plan explicitly.", file=sys.stderr)
        return 1

    output = args.output or (root / "previews" / "preview.html")
    script = Path(__file__).with_name("build_preview.py")

    cmd = [
        sys.executable,
        str(script),
        str(shot_plan),
        "--output",
        str(output),
    ]
    if args.style:
        cmd.extend(["--style", args.style])

    prompts = args.prompts or prefer(root, ["video_prompts.json", "planning/video_prompts.json"], ["*video_prompt*.json", "*prompts*.json"])
    climax = args.climax or prefer(root.parent, ["audio/suno_v3_90s/candidate_b_original_climax.json"], ["*climax*.json"])
    director_score = args.director_score or prefer(root, ["planning/director_score.json", "planning/director_score_v4.json"], ["*director_score*.json"])
    final_dir = root / "videos" / "final"
    final_video = args.final_video or (latest(final_dir, ["*.mp4"]) if final_dir.exists() else None)
    focus_video = args.focus_video
    contact_sheet = args.contact_sheet or (latest(final_dir, ["*contact*.jpg", "*contact*.png"]) if final_dir.exists() else None)
    edl = args.edl or (latest(final_dir, ["*edl.json"]) if final_dir.exists() else None)
    edit_decision = args.edit_decision_qc or (latest(final_dir, ["edit_decision_qc.json"]) if final_dir.exists() else None)

    add_path(cmd, "--prompts", prompts)
    add_path(cmd, "--climax", climax)
    add_path(cmd, "--director-score", director_score)
    add_path(cmd, "--final-video", final_video)
    add_path(cmd, "--focus-video", focus_video)
    add_path(cmd, "--contact-sheet", contact_sheet)
    add_path(cmd, "--edl", edl)
    add_path(cmd, "--edit-decision-qc", edit_decision)

    for flag, directory in (
        ("--keyframe-dir", root / "assets" / "keyframes"),
        ("--video-dir", root / "videos" / "seedance"),
        ("--qc-video-dir", root / "videos" / "seedance" / "qc_audio"),
        ("--proof-dir", root / "videos" / "final" / "lipsync_proof"),
    ):
        if directory.exists():
            cmd.extend([flag, str(directory)])

    asset_review = latest(root / "assets", ["*asset*review*.png", "*asset*review*.jpg", "*cast*.png", "*cast*.jpg"]) if (root / "assets").exists() else None
    add_path(cmd, "--asset-review", asset_review)
    manifest = latest(root, ["*asset*manifest*.json", "*asset_review*.json"])
    add_path(cmd, "--asset-review-manifest", manifest)

    print(" ".join(cmd))
    if args.dry_run:
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    return subprocess.run(cmd).returncode


if __name__ == "__main__":
    sys.exit(main())
