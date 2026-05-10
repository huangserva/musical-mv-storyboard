#!/usr/bin/env python3
"""Find music climax windows from an audio file using ffmpeg-decoded PCM.

This is intentionally lightweight: it does not require librosa. It scores
short windows by smoothed RMS energy plus energy-rise onset, then writes the
top non-overlapping 2s and 4s windows. Use this before deciding lip-sync shots.
"""

from __future__ import annotations

import argparse
import array
import json
import math
import subprocess
import sys
from pathlib import Path


def decode_mono_f32(audio_path: Path, sample_rate: int) -> array.array:
    raw = subprocess.check_output(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(audio_path),
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-f",
            "f32le",
            "-",
        ]
    )
    samples = array.array("f")
    samples.frombytes(raw)
    return samples


def moving_average(values: list[float], radius: int) -> list[float]:
    if radius <= 0:
        return values[:]
    out: list[float] = []
    for i in range(len(values)):
        start = max(0, i - radius)
        end = min(len(values), i + radius + 1)
        out.append(sum(values[start:end]) / max(end - start, 1))
    return out


def normalize(values: list[float]) -> list[float]:
    if not values:
        return []
    low = min(values)
    high = max(values)
    span = high - low
    if span <= 1e-12:
        return [0.0 for _ in values]
    return [(v - low) / span for v in values]


def rms_frames(samples: array.array, sample_rate: int, window_s: float, hop_s: float) -> tuple[list[float], list[float]]:
    window = max(1, int(window_s * sample_rate))
    hop = max(1, int(hop_s * sample_rate))
    times: list[float] = []
    values: list[float] = []
    for start in range(0, max(1, len(samples) - window + 1), hop):
        chunk = samples[start : start + window]
        if not chunk:
            continue
        energy = math.sqrt(sum(float(x) * float(x) for x in chunk) / len(chunk) + 1e-12)
        times.append(start / sample_rate)
        values.append(energy)
    return times, values


def score_windows(
    times: list[float],
    energy_norm: list[float],
    onset_norm: list[float],
    duration: float,
    window_s: float,
    step_s: float,
    top_k: int,
) -> list[dict]:
    candidates: list[tuple[float, float, float, float, float]] = []
    start = 0.0
    while start <= max(duration - window_s, 0):
        end = start + window_s
        idx = [i for i, t in enumerate(times) if start <= t < end]
        if idx:
            energy = sum(energy_norm[i] for i in idx) / len(idx)
            onset = max(onset_norm[i] for i in idx)
            score = 0.65 * energy + 0.35 * onset
            candidates.append((score, start, end, energy, onset))
        start += step_s

    selected: list[tuple[float, float, float, float, float]] = []
    for item in sorted(candidates, reverse=True):
        _, start, end, _, _ = item
        if all(not (max(start, s) < min(end, e)) for _, s, e, _, _ in selected):
            selected.append(item)
        if len(selected) >= top_k:
            break

    return [
        {
            "start": round(start, 2),
            "end": round(end, 2),
            "duration": round(end - start, 2),
            "score": round(score, 3),
            "energy": round(energy, 3),
            "onset": round(onset, 3),
        }
        for score, start, end, energy, onset in sorted(selected, key=lambda x: x[1])
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Find music climax windows from an audio file")
    parser.add_argument("audio", help="Audio path")
    parser.add_argument("--output", default="music_climax_analysis.json", help="Output JSON path")
    parser.add_argument("--sample-rate", type=int, default=22050)
    parser.add_argument("--top-k", type=int, default=10)
    args = parser.parse_args()

    audio_path = Path(args.audio).expanduser().resolve()
    if not audio_path.exists():
        print(f"Error: {audio_path} not found", file=sys.stderr)
        sys.exit(1)

    samples = decode_mono_f32(audio_path, args.sample_rate)
    duration = len(samples) / args.sample_rate
    times, rms = rms_frames(samples, args.sample_rate, window_s=0.5, hop_s=0.1)
    smoothed = moving_average(rms, radius=3)
    energy_norm = normalize(smoothed)
    onset = [0.0]
    for prev, cur in zip(smoothed, smoothed[1:]):
        onset.append(max(0.0, cur - prev))
    onset_norm = normalize(onset)

    output = {
        "source": str(audio_path),
        "duration": round(duration, 3),
        "method": "ffmpeg mono f32 PCM; 0.5s RMS / 0.1s hop; score = 0.65 mean normalized energy + 0.35 max normalized energy-rise onset",
        "top_2s_windows": score_windows(times, energy_norm, onset_norm, duration, 2.0, 0.25, args.top_k),
        "top_4s_windows": score_windows(times, energy_norm, onset_norm, duration, 4.0, 0.25, args.top_k),
    }

    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Climax analysis: {output_path}")
    print("Top 4s windows:")
    for item in output["top_4s_windows"]:
        print(
            f"  {item['start']:>6.2f}-{item['end']:>6.2f}s "
            f"score={item['score']:.3f} energy={item['energy']:.3f} onset={item['onset']:.3f}"
        )


if __name__ == "__main__":
    main()
