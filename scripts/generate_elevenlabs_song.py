#!/usr/bin/env python3
"""Generate a vocal musical/MV song with ElevenLabs Music API."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests
import yaml


DEFAULT_CONFIG = Path.home() / ".hermes/skills/shared-lib/config.yaml"
DEFAULT_ELEVENLABS_BASE = "https://api.elevenlabs.io"


def read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def mask_secret(value: str) -> str:
    if len(value) <= 12:
        return "***"
    return f"{value[:8]}...{value[-4:]}"


def load_elevenlabs_config(config_path: Path) -> tuple[str, str]:
    config = read_yaml(config_path)
    section = config.get("ElevenLabs") if isinstance(config.get("ElevenLabs"), dict) else {}
    api_key = (
        os.getenv("ELEVENLABS_API_KEY")
        or os.getenv("XI_API_KEY")
        or section.get("api_key")
        or ""
    )
    api_base = os.getenv("ELEVENLABS_API_BASE") or section.get("api_base") or DEFAULT_ELEVENLABS_BASE
    if not api_key:
        raise SystemExit(
            "ElevenLabs API key not found. Set ELEVENLABS_API_KEY/XI_API_KEY "
            f"or configure ElevenLabs.api_key in {config_path}"
        )
    return str(api_base).rstrip("/"), str(api_key)


def build_prompt(args: argparse.Namespace) -> str:
    lyrics = ""
    if args.lyrics_file:
        lyrics = Path(args.lyrics_file).expanduser().resolve().read_text(encoding="utf-8").strip()
    elif args.lyrics:
        lyrics = args.lyrics.strip()

    parts = [
        "Create a complete musical/MV song.",
        "This must include clear sung vocals unless explicitly marked instrumental.",
        f"Style and scene: {args.style.strip()}",
    ]
    if args.vocal:
        parts.append(f"Vocal direction: {args.vocal.strip()}")
    if args.arrangement:
        parts.append(f"Arrangement: {args.arrangement.strip()}")
    if lyrics:
        parts.append("Use these lyrics exactly as the main lyric source:")
        parts.append(lyrics)
    else:
        parts.append("Write original lyrics that fit the scene and make the hook memorable.")
    if not args.instrumental:
        parts.append("Do not make it instrumental. Do not use gibberish vocals. Lyrics must be audible and intelligible.")
    return "\n\n".join(parts).strip()


def build_payload(args: argparse.Namespace, prompt: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "prompt": prompt,
        "music_length_ms": args.duration_ms,
        "model_id": args.model_id,
        "force_instrumental": bool(args.instrumental),
    }
    if args.seed is not None:
        payload["seed"] = args.seed
    return payload


def compose(
    api_base: str,
    api_key: str,
    payload: dict[str, Any],
    output_path: Path,
    output_format: str,
    timeout: int,
) -> dict[str, Any]:
    started = time.time()
    params = {"output_format": output_format} if output_format else {}
    response = requests.post(
        f"{api_base}/v1/music",
        params=params,
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
        json=payload,
        timeout=timeout,
    )
    content_type = response.headers.get("content-type", "")
    if response.status_code >= 400:
        try:
            detail = response.json()
        except ValueError:
            detail = {"text": response.text[:1000]}
        raise RuntimeError(f"ElevenLabs music generation failed: HTTP {response.status_code}: {detail}")
    if "json" in content_type:
        try:
            detail = response.json()
        except ValueError:
            detail = {"text": response.text[:1000]}
        raise RuntimeError(f"ElevenLabs returned JSON instead of audio: {detail}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(response.content)
    return {
        "output_bytes": output_path.stat().st_size,
        "content_type": content_type,
        "request_id": response.headers.get("request-id") or response.headers.get("x-request-id"),
        "elapsed_sec": round(time.time() - started, 3),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate vocal music for musical/MV projects via ElevenLabs")
    parser.add_argument("--style", required=True, help="Scene, genre, instruments, BPM, mood, production")
    parser.add_argument("--lyrics", default="", help="Inline lyrics")
    parser.add_argument("--lyrics-file", default="", help="Lyrics text file")
    parser.add_argument("--vocal", default="", help="Vocal persona/direction")
    parser.add_argument("--arrangement", default="", help="Song section arrangement and energy arc")
    parser.add_argument("--duration-ms", type=int, required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--manifest", default="", help="Default: <output>.json")
    parser.add_argument("--prompt-out", default="", help="Default: <output>.prompt.txt")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--instrumental", action="store_true", help="Only use when no vocals are desired")
    parser.add_argument("--model-id", default="music_v1")
    parser.add_argument("--output-format", default="mp3_44100_192")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--timeout", type=int, default=300)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.duration_ms <= 0:
        raise SystemExit("--duration-ms must be positive")
    if args.lyrics and args.lyrics_file:
        raise SystemExit("use either --lyrics or --lyrics-file, not both")

    output_path = Path(args.output).expanduser().resolve()
    manifest_path = Path(args.manifest).expanduser().resolve() if args.manifest else output_path.with_suffix(".json")
    prompt_path = Path(args.prompt_out).expanduser().resolve() if args.prompt_out else output_path.with_suffix(".prompt.txt")

    api_base, api_key = load_elevenlabs_config(Path(args.config).expanduser().resolve())
    prompt = build_prompt(args)
    payload = build_payload(args, prompt)

    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(prompt + "\n", encoding="utf-8")
    manifest: dict[str, Any] = {
        "provider": "elevenlabs",
        "api_base": api_base,
        "api_key_masked": mask_secret(api_key),
        "endpoint": "/v1/music",
        "output": str(output_path),
        "prompt_path": str(prompt_path),
        "output_format": args.output_format,
        "payload": payload,
        "api_called": False,
    }

    if args.dry_run:
        write_json(manifest_path, manifest)
        print(f"[dry-run] prompt={prompt_path} manifest={manifest_path}")
        return

    result = compose(
        api_base=api_base,
        api_key=api_key,
        payload=payload,
        output_path=output_path,
        output_format=args.output_format,
        timeout=args.timeout,
    )
    manifest["api_called"] = True
    manifest["result"] = result
    write_json(manifest_path, manifest)
    print(f"[ok] output={output_path} bytes={result['output_bytes']:,} manifest={manifest_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise
