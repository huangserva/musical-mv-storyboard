# Musical MV Storyboard

Music-first workflow for making AI-assisted musical videos and MV-style short films.

This skill helps an agent plan and produce a music video from the song outward: lyrics, vocals, climax windows, short lip-sync moments, keyframes, Seedance video generation, EDL, preview page, and final ffmpeg post-production.

## What It Is For

- 真人音乐剧 / 唱跳 MV
- 剧情 MV / 情绪 MV
- AI 生成歌曲配视频
- 需要少量短对口型、更多 B-roll / 群舞 / 氛围镜头的项目

The core principle is simple: **the song is the master timeline**. Visuals, captions, covers, overlays, and edits must serve the music timing, not the other way around.

## Key Rules

- Analyze music climax windows before designing shots.
- Use short lip-sync clips, usually 3-4 seconds, not long continuous lip-sync by default.
- For Seedance MV generation, use `generate_audio: false`; final audio comes from the master song.
- Freeze confirmed A/B/C lip-sync offsets in the EDL.
- Cover/title cards default to replacing the first N seconds, not inserting time before the main edit.
- Always maintain `preview.html` as the director review board.
- Always export final lip-sync proof clips from the final video itself.

## Workflow

1. Lock or generate the song.
2. Analyze lyrics, vocal timing, beat, energy, and climax windows.
3. Build a timeline and initial shot classification.
4. Let the director/LLM revise the shot plan around the real musical peaks.
5. Generate keyframes and update `preview.html`.
6. Generate Seedance clips serially, with cost control.
7. Build the EDL and final edit with ffmpeg.
8. Export contact sheets and lip-sync proof clips.

## Main Files

- `SKILL.md` - core operating instructions.
- `references/lip-sync-policy.md` - short lip-sync strategy and post-production timing rules.
- `references/workflow.md` - end-to-end workflow reference.
- `references/director-template.md` - structured director planning template.
- `references/prompt-craft.md` - image/video prompt guidance.
- `references/shot-types.md` - shot type definitions.
- `scripts/analyze_audio.py` - Whisper + audio feature analysis.
- `scripts/analyze_climax_windows.py` - climax window detection.
- `scripts/build_music_timeline.py` - timeline construction.
- `scripts/classify_musical_shots.py` - first-pass shot classification.
- `scripts/build_video_prompts.py` - generate creative prompts from a shot plan.
- `scripts/build_preview.py` - generate the review-board `preview.html`.
- `scripts/generate_elevenlabs_song.py` - ElevenLabs music generation helper.

## Typical Command Flow

```bash
python scripts/analyze_audio.py song.mp3 --language zh --output audio_analysis.json
python scripts/analyze_climax_windows.py song.mp3 --output music_climax_analysis.json
python scripts/build_music_timeline.py audio_analysis.json --output music_timeline.json
python scripts/classify_musical_shots.py music_timeline.json --output shot_plan.auto.json
```

After the director plan is revised, generate prompts and preview:

```bash
python scripts/build_video_prompts.py shot_plan.director.json --output video_prompts.json
python scripts/build_preview.py shot_plan.director.json \
  --prompts video_prompts.json \
  --climax music_climax_analysis.json \
  --output previews/preview.html
```

## Notes

This repository contains only the skill code and documentation. It does not include generated videos, audio files, API keys, or project assets.

