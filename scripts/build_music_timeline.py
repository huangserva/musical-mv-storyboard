#!/usr/bin/env python3
"""Build music timeline from audio_analysis.json.

Reads the actual section detection from analyze_audio.py and produces
a structured timeline with per-section lyric mapping.

Input:  audio_analysis.json (from analyze_audio.py)
Output: music_timeline.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def build_timeline(analysis: dict) -> dict:
    """Convert audio analysis into a structured timeline."""
    sections = analysis.get("sections", [])
    segments = analysis.get("whisper_segments", [])
    vocal_activity = analysis.get("vocal_activity", [])
    beat_map = analysis.get("beat_map", [])
    energy_curve = analysis.get("energy_curve", {})

    # Map whisper segments to sections
    timeline_sections = []
    for sec in sections:
        # Find all whisper segments that fall within this section
        sec_lyrics = []
        for seg in segments:
            seg_mid = (seg["start"] + seg["end"]) / 2
            if seg["start"] >= sec["start"] and seg["end"] <= sec["end"]:
                sec_lyrics.append(seg["text"])
            elif sec["start"] <= seg_mid <= sec["end"]:
                sec_lyrics.append(seg["text"])

        # Compute section-level vocal stats
        sec_vocal = [
            va for va in vocal_activity
            if va["start"] >= sec["start"] and va["end"] <= sec["end"]
        ]
        vocal_seconds = sum(1 for v in sec_vocal if v["has_vocal"])
        total_seconds = len(sec_vocal) if sec_vocal else 1
        vocal_density = round(vocal_seconds / total_seconds, 2) if total_seconds > 0 else 0.0

        # Find beats in section
        sec_beats = [
            round(b - sec["start"], 3)
            for b in beat_map
            if sec["start"] <= b <= sec["end"]
        ]

        # Energy stats
        e_ts = energy_curve.get("timestamps", [])
        e_vals = energy_curve.get("values", [])
        sec_energy = [
            v for t, v in zip(e_ts, e_vals)
            if sec["start"] <= t <= sec["end"]
        ]
        avg_energy = round(sum(sec_energy) / len(sec_energy), 3) if sec_energy else 0.0
        peak_energy = round(max(sec_energy), 3) if sec_energy else 0.0

        timeline_sections.append({
            "id": f"section_{len(timeline_sections):02d}",
            "label": sec["label"],
            "start": sec["start"],
            "end": sec["end"],
            "duration": sec["duration"],
            "vocal_density": vocal_density,
            "avg_energy": avg_energy,
            "peak_energy": peak_energy,
            "beats": sec_beats,
            "lyrics": sec_lyrics,
            "whisper_segments": [
                s for s in segments
                if s["start"] >= sec["start"] and s["end"] <= sec["end"]
            ],
        })

    # Compute song-wide stats
    all_densities = [s["vocal_density"] for s in timeline_sections]
    all_energies = [s["avg_energy"] for s in timeline_sections]
    max_density = max(all_densities) if all_densities else 1.0
    max_energy = max(all_energies) if all_energies else 1.0

    # Normalize
    for s in timeline_sections:
        s["vocal_density_norm"] = round(s["vocal_density"] / max_density, 2) if max_density > 0 else 0
        s["energy_norm"] = round(s["avg_energy"] / max_energy, 2) if max_energy > 0 else 0

    return {
        "duration": analysis.get("duration", 0),
        "tempo_bpm": analysis.get("tempo_bpm", 0),
        "source": analysis.get("source", ""),
        "sections": timeline_sections,
        "stats": {
            "total_sections": len(timeline_sections),
            "has_vocal_sections": sum(1 for s in timeline_sections if s["vocal_density"] > 0.3),
            "peak_section": max(timeline_sections, key=lambda s: s["peak_energy"])["label"] if timeline_sections else "none",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build music timeline from audio analysis")
    parser.add_argument("analysis", help="Path to audio_analysis.json")
    parser.add_argument("--output", default="music_timeline.json", help="Output path")
    args = parser.parse_args()

    analysis_path = Path(args.analysis).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    if not analysis_path.exists():
        print(f"Error: {analysis_path} not found", file=sys.stderr)
        sys.exit(1)

    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    timeline = build_timeline(analysis)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")

    # Summary
    print(f"Timeline: {output_path}")
    print(f"  Duration: {timeline['duration']}s | BPM: {timeline['tempo_bpm']}")
    print(f"  Sections: {timeline['stats']['total_sections']} "
          f"({timeline['stats']['has_vocal_sections']} with vocals)")
    for sec in timeline["sections"]:
        print(f"    [{sec['start']:>6.1f}s - {sec['end']:>6.1f}s] {sec['label']:<12s} "
              f"vocal={sec['vocal_density']:.0%} energy={sec['avg_energy']:.2f} "
              f"beats={len(sec['beats'])}")


if __name__ == "__main__":
    main()
