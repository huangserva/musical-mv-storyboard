# Musical MV Storyboard

Music-first workflow for making AI-assisted musical videos and MV-style short films.

This skill helps an agent plan and produce a music video from the song outward: lyrics, vocals, climax windows, short lip-sync moments, voice direction, keyframes, Seedance video generation, EDL, preview page, and final ffmpeg post-production.

## What It Is For

- 真人音乐剧 / 唱跳 MV
- 剧情 MV / 情绪 MV
- AI 生成歌曲配视频
- 需要少量短对口型、更多 B-roll / 群舞 / 氛围镜头的项目

The core principle is simple: **the song is the master timeline**. Visuals, captions, covers, overlays, and edits must serve the music timing, not the other way around.

V2 adds a second core principle: **voice must be directed, not merely generated**. For narration, TTS, cloned voice, or vocal performance, create a voice director plan, audition the strongest 15-20 seconds, then freeze the accepted voice template before long-form generation.

## Key Rules

- Analyze music climax windows before designing shots.
- Create `voice_director_plan.json` before long TTS / narration / vocal clone generation.
- Confirm A/B/C voice auditions before generating full-length voice.
- Use short lip-sync clips, usually 3-4 seconds, not long continuous lip-sync by default.
- For Seedance MV generation, use `generate_audio: false`; final audio comes from the master song.
- Freeze confirmed A/B/C lip-sync offsets in the EDL.
- Cover/title cards default to replacing the first N seconds, not inserting time before the main edit.
- Always maintain `preview.html` as the director review board.
- Always export final lip-sync proof clips from the final video itself.

## Workflow

1. Lock or generate the song.
2. Build the voice director plan when the project needs narration, TTS, cloned voice, or vocal performance.
3. Analyze lyrics, vocal timing, beat, energy, and climax windows.
4. Build a timeline and initial shot classification.
5. Let the director/LLM revise the shot plan around the real musical peaks.
6. Generate keyframes and update `preview.html`.
7. Generate Seedance clips serially, with cost control.
8. Build the EDL and final edit with ffmpeg.
9. Export contact sheets and lip-sync proof clips.
10. Validate the audio lock before delivery.

## Main Files

- `SKILL.md` - core operating instructions.
- `references/lip-sync-policy.md` - short lip-sync strategy and post-production timing rules.
- `references/voice-direction.md` - voice director plan, A/B/C audition, accepted voice template.
- `references/audio-lock-policy.md` - master audio timeline, cover replace/insert policy, EDL gates.
- `references/post-production-sound.md` - EQ, compression, loudness, ducking, voice finishing.
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
- `scripts/export_lipsync_proofs.py` - export proof clips from the final video itself.
- `scripts/validate_audio_lock.py` - validate EDL timing, cover mode, lip-sync offsets, final duration.

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
  --proof-dir videos/final/lipsync_proof \
  --output previews/preview.html
```

Before delivery, export final proof clips and validate the audio lock:

```bash
python scripts/export_lipsync_proofs.py final_edl.json \
  --final-video final_output.mp4 \
  --output-dir lipsync_proof \
  --update-edl

python scripts/validate_audio_lock.py final_edl.json \
  --final-video final_output.mp4 \
  --require-proofs
```

## Notes

This repository contains only the skill code and documentation. It does not include generated videos, audio files, API keys, or project assets.
