#!/usr/bin/env python3
"""Audio analysis: Whisper transcription + librosa beat/energy/section detection.

Produces audio_analysis.json with word-level timestamps, vocal activity map,
beat map, energy curve, tempo, and automatic section detection.

Dependencies: mlx-whisper, librosa, ffmpeg (on PATH)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import librosa
import mlx_whisper

# ─── Whisper transcription ──────────────────────────────────────────────────


def transcribe(audio_path: str, language: str = "en") -> dict:
    """Transcribe audio with mlx-whisper, return result dict."""
    result = mlx_whisper.transcribe(
        audio_path,
        path_or_hf_repo="mlx-community/whisper-large-v3-turbo",
        word_timestamps=True,
        language=language,
    )
    return result


def extract_vocal_activity(segments: list[dict], total_duration: float, resolution: float = 0.5) -> list[dict]:
    """Build a binary vocal activity map at given time resolution (seconds)."""
    activity = []
    t = 0.0
    while t < total_duration:
        t_end = t + resolution
        has_vocal = any(
            seg["start"] < t_end and seg["end"] > t
            for seg in segments
            if seg.get("text", "").strip()
        )
        activity.append({"start": round(t, 2), "end": round(min(t_end, total_duration), 2), "has_vocal": has_vocal})
        t = t_end
    return activity


# ─── librosa analysis ───────────────────────────────────────────────────────


def analyze_beats(y, sr) -> list[float]:
    """Return beat timestamps."""
    _, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    return [round(float(librosa.frames_to_time(f, sr=sr)), 3) for f in beat_frames]


def analyze_energy(y, sr, hop_length: int = 512, resolution: float = 0.5) -> dict:
    """Compute RMS energy curve at given time resolution."""
    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
    timestamps = librosa.frames_to_time(range(len(rms)), sr=sr, hop_length=hop_length)

    # Downsample to target resolution
    if timestamps[-1] > 0:
        n_bins = int(timestamps[-1] / resolution) + 1
    else:
        n_bins = 1
    ts_bins = [round(i * resolution, 2) for i in range(n_bins)]
    val_bins = [0.0] * n_bins

    for raw_t, raw_v in zip(timestamps, rms):
        idx = min(int(raw_t / resolution), n_bins - 1)
        val_bins[idx] = max(val_bins[idx], float(raw_v))

    # Normalize to 0-1
    max_val = max(val_bins) if val_bins else 1.0
    if max_val > 0:
        val_bins = [round(v / max_val, 4) for v in val_bins]

    return {"timestamps": ts_bins, "values": val_bins}


def detect_sections(
    energy_curve: dict,
    vocal_activity: list[dict],
    total_duration: float,
) -> list[dict]:
    """Detect song sections based on energy + vocal activity patterns.

    Strategy:
    1. Compute rolling average energy over ~8s windows
    2. Find energy peaks and valleys
    3. Use vocal density to distinguish intro/outro (low vocal) from verse/chorus
    4. Label sections: intro, verse, pre_chorus, chorus, bridge, drop, outro
    """
    values = energy_curve["values"]
    timestamps = energy_curve["timestamps"]
    resolution = timestamps[1] - timestamps[0] if len(timestamps) > 1 else 0.5

    # Rolling average over ~8s window
    window_size = max(1, int(8.0 / resolution))
    smoothed = []
    for i in range(len(values)):
        start = max(0, i - window_size // 2)
        end = min(len(values), i + window_size // 2 + 1)
        smoothed.append(sum(values[start:end]) / (end - start))

    # Find vocal density per window
    vocal_density_map = {}
    for va in vocal_activity:
        idx = int(va["start"] / resolution) if resolution > 0 else 0
        key = min(idx, len(smoothed) - 1)
        if key not in vocal_density_map:
            vocal_density_map[key] = {"total": 0, "vocal": 0}
        vocal_density_map[key]["total"] += 1
        if va["has_vocal"]:
            vocal_density_map[key]["vocal"] += 1

    # Split into segments by energy changes
    threshold = 0.15
    segments = []
    seg_start = 0
    for i in range(1, len(smoothed)):
        if abs(smoothed[i] - smoothed[i - 1]) > threshold:
            segments.append((seg_start, i))
            seg_start = i
    segments.append((seg_start, len(smoothed)))

    if not segments:
        segments = [(0, len(smoothed))]

    # Compute vocal density per segment
    def get_vocal_density(start_idx, end_idx):
        total = 0
        vocal = 0
        for idx in range(start_idx, end_idx):
            info = vocal_density_map.get(idx, {"total": 1, "vocal": 0})
            total += info["total"]
            vocal += info["vocal"]
        return round(vocal / total, 2) if total > 0 else 0.0

    # Compute average energy per segment
    def get_avg_energy(start_idx, end_idx):
        vals = smoothed[start_idx:end_idx]
        return round(sum(vals) / len(vals), 3) if vals else 0.0

    # Classify each segment
    avg_energies = [get_avg_energy(s, e) for s, e in segments]
    overall_energy = sum(avg_energies) / len(avg_energies) if avg_energies else 0.5
    max_energy = max(avg_energies) if avg_energies else 1.0

    sections = []
    prev_label = None
    for i, (start_idx, end_idx) in enumerate(segments):
        start_t = timestamps[start_idx] if start_idx < len(timestamps) else 0.0
        end_t = timestamps[end_idx - 1] if end_idx > 0 and (end_idx - 1) < len(timestamps) else total_duration
        end_t = min(end_t + resolution, total_duration)

        vd = get_vocal_density(start_idx, end_idx)
        ae = get_avg_energy(start_idx, end_idx)
        duration = end_t - start_t

        # Skip tiny segments (< 3s)
        if duration < 3.0:
            if sections:
                sections[-1]["end"] = end_t
                sections[-1]["duration"] = round(sections[-1]["end"] - sections[-1]["start"], 2)
            continue

        # Label logic
        rel_energy = ae / max_energy if max_energy > 0 else 0.5
        label = _classify_section(vd, rel_energy, start_t, total_duration, prev_label, sections)

        sections.append({
            "start": round(start_t, 2),
            "end": round(end_t, 2),
            "duration": round(duration, 2),
            "label": label,
            "vocal_density": vd,
            "avg_energy": ae,
        })
        prev_label = label

    # Merge adjacent same-label sections
    merged = []
    for sec in sections:
        if merged and merged[-1]["label"] == sec["label"]:
            merged[-1]["end"] = sec["end"]
            merged[-1]["duration"] = round(merged[-1]["end"] - merged[-1]["start"], 2)
            merged[-1]["vocal_density"] = round(
                (merged[-1]["vocal_density"] + sec["vocal_density"]) / 2, 2
            )
            merged[-1]["avg_energy"] = round(
                (merged[-1]["avg_energy"] + sec["avg_energy"]) / 2, 3
            )
        else:
            merged.append(sec)

    return merged


def _classify_section(
    vocal_density: float,
    rel_energy: float,
    time_pos: float,
    total_duration: float,
    prev_label: str | None,
    all_sections: list[dict],
) -> str:
    """Classify a section based on features."""
    is_early = time_pos < total_duration * 0.15
    is_late = time_pos > total_duration * 0.85

    if is_early and vocal_density < 0.3:
        return "intro"
    if is_late and vocal_density < 0.3:
        return "outro"

    # Count existing labels for alternation
    chorus_count = sum(1 for s in all_sections if s["label"] == "chorus")
    verse_count = sum(1 for s in all_sections if s["label"] == "verse")

    # High energy + high vocal → likely chorus
    if rel_energy > 0.7 and vocal_density > 0.5:
        return "chorus"

    # Medium energy, medium vocal → verse or pre_chorus
    if vocal_density > 0.3:
        if prev_label == "verse":
            return "pre_chorus"
        return "verse"

    # Low vocal, high energy → drop / instrumental break
    if rel_energy > 0.5 and vocal_density < 0.2:
        return "drop"

    # Low vocal, low energy → bridge or outro-like
    if vocal_density < 0.2:
        return "bridge"

    # Fallback: alternate verse/chorus
    if chorus_count <= verse_count:
        return "chorus"
    return "verse"


# ─── Main ───────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Audio analysis: Whisper + librosa")
    parser.add_argument("audio", help="Path to audio file (mp3, wav, etc.)")
    parser.add_argument("--language", default="en", help="Language for Whisper (en/zh)")
    parser.add_argument("--output", help="Output JSON path (default: audio_analysis.json)")
    args = parser.parse_args()

    audio_path = Path(args.audio).expanduser().resolve()
    if not audio_path.exists():
        print(f"Error: {audio_path} not found", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output or "audio_analysis.json").expanduser().resolve()

    # Convert to 16kHz mono WAV for Whisper
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_wav = tmp.name

    print(f"[1/4] Converting to 16kHz mono WAV...")
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(audio_path), "-ar", "16000", "-ac", "1", tmp_wav],
        capture_output=True,
        check=True,
    )

    # Whisper transcription
    print(f"[2/4] Running Whisper transcription ({args.language})...")
    whisper_result = transcribe(tmp_wav, language=args.language)
    segments = whisper_result.get("segments", [])

    # Load original audio for librosa
    print(f"[3/4] Running librosa analysis...")
    y, sr = librosa.load(str(audio_path), sr=None, mono=True)
    total_duration = round(float(librosa.get_duration(y=y, sr=sr)), 2)

    # Analyze
    vocal_activity = extract_vocal_activity(segments, total_duration)
    beat_map = analyze_beats(y, sr)
    energy_curve = analyze_energy(y, sr)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    tempo_bpm = round(float(tempo.item()), 1) if hasattr(tempo, 'item') else round(float(tempo), 1) if tempo else 120.0

    # Detect sections
    sections = detect_sections(energy_curve, vocal_activity, total_duration)

    # Clean up
    Path(tmp_wav).unlink(missing_ok=True)

    # Build output
    output = {
        "source": str(audio_path),
        "duration": total_duration,
        "tempo_bpm": tempo_bpm,
        "whisper_segments": [
            {
                "start": round(s["start"], 2),
                "end": round(s["end"], 2),
                "text": s.get("text", "").strip(),
                "words": [
                    {"start": round(w["start"], 2), "end": round(w["end"], 2), "word": w.get("word", "")}
                    for w in s.get("words", [])
                ] if "words" in s else [],
            }
            for s in segments
        ],
        "vocal_activity": vocal_activity,
        "beat_map": beat_map,
        "energy_curve": energy_curve,
        "sections": sections,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    # Summary
    print(f"[4/4] Done! Output: {output_path}")
    print(f"  Duration: {total_duration}s | BPM: {tempo_bpm}")
    print(f"  Vocal segments: {len(segments)}")
    print(f"  Beats: {len(beat_map)}")
    print(f"  Sections detected: {len(sections)}")
    for sec in sections:
        print(f"    [{sec['start']:>6.1f}s - {sec['end']:>6.1f}s] {sec['label']:<12s} "
              f"vocal={sec['vocal_density']:.0%} energy={sec['avg_energy']:.2f}")


if __name__ == "__main__":
    main()
