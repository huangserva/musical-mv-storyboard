#!/usr/bin/env python3
"""Build creative video prompts from a shot plan.

Reads shot_plan.json (with director notes filled in) and produces
provider-ready video prompts for Seedance I2V.

Input:  shot_plan.json (director-filled)
Output: video_prompts.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


# Shot-type-specific prompt structures
SHOT_PROMPT_TEMPLATES = {
    "lip_sync_closeup": {
        "image_hint": "stable frontal face, clear mouth visibility, singing posture",
        "motion_base": "subtle head movement, gentle hair sway, breathing motion, lip motion from singing",
        "camera_default": "slow push-in or static, eye-level, medium close-up to close-up",
    },
    "performance_medium": {
        "image_hint": "half-body visible, expressive posture, environmental context",
        "motion_base": "walking, gesturing, turning, interacting with environment",
        "camera_default": "tracking or dolly, medium shot, slight angle",
    },
    "dance_or_group": {
        "image_hint": "dynamic group composition, choreography pose, stage or open space",
        "motion_base": "synchronized dance movements, explosive choreography, group formations shifting",
        "camera_default": "wide or medium-wide, low angle for impact, crane or tracking",
    },
    "mv_broll": {
        "image_hint": "atmospheric landscape or interior, symbolic objects, mood and texture",
        "motion_base": "slow camera drift, natural elements moving (wind, water, light), time-lapse feel",
        "camera_default": "slow aerial or dolly, wide establishing, smooth and cinematic",
    },
    "transition": {
        "image_hint": "abstract or transitional visual element",
        "motion_base": "fast camera movement, wipe, dissolve, or morph between scenes",
        "camera_default": "whip pan, rack focus, or speed ramp",
    },
}


NO_AUDIO_INSTRUCTION = (
    "No independent music or BGM in the generated clip; "
    "final song will be added in post."
)


def ensure_no_audio_instruction(prompt: str) -> str:
    """Make Seedance video prompts safe for MV post-production audio."""
    markers = (
        "No independent music",
        "no independent music",
        "No BGM",
        "no BGM",
        "不要自带音乐",
        "不要自带独立音乐",
        "不要生成音乐",
        "不要生成BGM",
        "独立音乐",
        "最终会后期",
    )
    if any(marker in prompt for marker in markers):
        return prompt
    if prompt.endswith("."):
        return f"{prompt} {NO_AUDIO_INSTRUCTION}"
    return f"{prompt}. {NO_AUDIO_INSTRUCTION}"


def choose_seedance_model(shot: dict) -> str:
    """Route Seedance model by whether faces/real people matter."""
    explicit = shot.get("seedance_model")
    if explicit:
        return explicit

    shot_type = shot.get("shot_type", "mv_broll")
    text = " ".join(
        str(shot.get(key, ""))
        for key in (
            "visual_description",
            "director_intent",
            "lip_sync_notes",
            "seedance_image_prompt",
            "seedance_video_prompt",
        )
    ).lower()
    english_face_terms = {
        "face",
        "mouth",
        "lip",
        "sing",
        "singer",
        "woman",
        "man",
        "female",
        "male",
        "girl",
        "boy",
        "person",
        "people",
        "guard",
        "curator",
        "cleaner",
        "performer",
    }
    chinese_face_terms = (
        "人脸",
        "真人",
        "女主",
        "男主",
        "主唱",
        "对口型",
        "嘴",
        "脸",
    )
    english_tokens = set(re.findall(r"[a-z]+", text))
    if (
        shot_type in {"lip_sync_closeup", "performance_medium"}
        or bool(english_tokens & english_face_terms)
        or any(term in text for term in chinese_face_terms)
    ):
        return "doubao-seedance-2.0-face"
    return "doubao-seedance-2.0"


def build_prompt_for_shot(shot: dict, style: str = "") -> dict:
    """Build image prompt and video prompt for a single shot."""
    shot_type = shot.get("shot_type", "mv_broll")
    template = SHOT_PROMPT_TEMPLATES.get(shot_type, SHOT_PROMPT_TEMPLATES["mv_broll"])

    # If director filled in detailed prompts, use those directly
    if shot.get("seedance_image_prompt") and len(shot["seedance_image_prompt"]) > 20:
        image_prompt = shot["seedance_image_prompt"]
    else:
        # Build from components
        parts = []
        if style:
            parts.append(f"{style} style")
        parts.append(template["image_hint"])
        if shot.get("visual_description"):
            parts.append(shot["visual_description"])
        if shot.get("lighting"):
            parts.append(shot["lighting"])
        if shot.get("reference_style"):
            parts.append(f"inspired by {shot['reference_style']}")
        image_prompt = ", ".join(parts)

    if shot.get("seedance_video_prompt") and len(shot["seedance_video_prompt"]) > 20:
        video_prompt = shot["seedance_video_prompt"]
    else:
        parts = []
        parts.append(template["motion_base"])
        if shot_type == "lip_sync_closeup" and shot.get("lip_sync_notes"):
            parts.append(shot["lip_sync_notes"])
        if shot.get("camera") or template["camera_default"]:
            parts.append(f"Camera: {shot.get('camera') or template['camera_default']}")
        if shot.get("director_intent"):
            parts.append(f"Mood: {shot['director_intent']}")
        video_prompt = ". ".join(parts)

    video_prompt = ensure_no_audio_instruction(video_prompt)

    duration = round(shot["end"] - shot["start"], 1)
    target_lip_sync_duration = shot.get("target_lip_sync_duration")
    if shot_type == "lip_sync_closeup" and not target_lip_sync_duration:
        target_lip_sync_duration = min(4.0, duration)
    needs_director_lip_trim = shot.get("needs_director_lip_trim", False)
    if shot_type == "lip_sync_closeup" and duration > 5.0:
        needs_director_lip_trim = True
    seedance_duration = 5 if shot_type == "lip_sync_closeup" else min(15, max(5, round(duration)))

    return {
        "shot_id": shot["shot_id"],
        "shot_type": shot_type,
        "start": shot["start"],
        "end": shot["end"],
        "duration": duration,
        "requires_exact_lip_sync": shot.get("requires_exact_lip_sync", False),
        "target_lip_sync_duration": target_lip_sync_duration,
        "needs_director_lip_trim": needs_director_lip_trim,
        "music_reason": shot.get("music_reason", ""),
        "climax_window": shot.get("climax_window"),
        "image_prompt": image_prompt,
        "video_prompt": video_prompt,
        # Seedance I2V specific
        "seedance_duration": seedance_duration,
        "seedance_model": choose_seedance_model(shot),
        "seedance_size": "9:16",
        "seedance_resolution": "480p",
        "seedance_generate_audio": False,
        "lip_sync_lyric": shot.get("lip_sync_notes", ""),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build video prompts from shot plan")
    parser.add_argument("shot_plan", help="Path to shot_plan.json")
    parser.add_argument("--style", default="", help="Overall visual style (e.g. 'dark cyberpunk', 'golden hour cinematic')")
    parser.add_argument("--output", default="video_prompts.json", help="Output path")
    args = parser.parse_args()

    shot_plan_path = Path(args.shot_plan).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    if not shot_plan_path.exists():
        print(f"Error: {shot_plan_path} not found", file=sys.stderr)
        sys.exit(1)

    shot_plan = json.loads(shot_plan_path.read_text(encoding="utf-8"))
    shots = shot_plan.get("shots", [])

    prompts = [build_prompt_for_shot(s, args.style) for s in shots]

    payload = {
        "style": args.style or "cinematic music video",
        "duration": shot_plan.get("duration", 0),
        "total_clips": len(prompts),
        "lip_sync_clips": [p for p in prompts if p["requires_exact_lip_sync"]],
        "prompts": prompts,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # Summary
    print(f"Video prompts: {output_path}")
    print(f"  Total clips: {len(prompts)}")
    print(f"  Lip-sync clips: {len(payload['lip_sync_clips'])}")
    for p in prompts:
        marker = " 🔴" if p["requires_exact_lip_sync"] else ""
        print(f"  {p['shot_id']}  {p['shot_type']:<22s} {p['duration']}s{marker}")
        print(f"    IMG: {p['image_prompt'][:80]}...")
        print(f"    VID: {p['video_prompt'][:80]}...")


if __name__ == "__main__":
    main()
