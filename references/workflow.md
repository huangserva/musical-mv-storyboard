# Workflow Reference

End-to-end walkthrough of the musical MV storyboard pipeline, with realistic data examples.

---

## Pipeline Overview

```
song.mp3
  ↓ [optional but required for TTS/narration/cloned vocal]
voice_director_plan.json
  ↓ analyze_audio.py
audio_analysis.json
  ↓ analyze_climax_windows.py
music_climax_analysis.json
  ↓ build_music_timeline.py
music_timeline.json
  ↓ [extract clean complete vocal phrases]
lip_sync_phrase_map.json
  ↓ classify_musical_shots.py
shot_plan.auto.json
  ↓ [director/LLM revises with climax windows + phrase map]
shot_plan.director.json
  ↓ build_video_prompts.py
video_prompts.json
  ↓ [asset_review gate → cinematic keyframes → preview.html gate → Seedance I2V]
candidate clips
  ↓ [when 2+ candidates exist: score_edit_candidates.py]
edit_decision_qc.json
  ↓ [recommended candidate → draft EDL]
*_edl.json
  ↓ [prepare_final_edit.py hard gate]
final_edit_gate_report.json
  ↓ [ffmpeg]
final_output.mp4
  ↓ export_lipsync_proofs.py + validate_audio_lock.py
lipsync_proof/*.mp4 + validated EDL
```

---

## Step 1: Lock the Music

Either generate via ElevenLabs or use a user-provided file. Output: `song.mp3`.

Example: Chinese pop 唱跳 song, 90 seconds, 128 BPM.

### Step 1.5: Direct the Voice

If the project uses narration, TTS, cloned voice, or a generated vocal performance, create `voice_director_plan.json` before long-form generation.

Minimum required fields:
- `voice_goal`
- `reference_voice`
- `global_delivery`
- per-segment `visual_context`, `performance_intent`, `emotion`, `pace`, `pauses`, `emphasis`
- `audition_variants`

Generate only the strongest 15-20s first. After the user selects A/B/C, freeze `accepted_voice_template`. Do not split long voice sentence-by-sentence unless the model requires it.

---

## Step 2: Audio Analysis

Run `scripts/analyze_audio.py` on `song.mp3`. This produces `audio_analysis.json` with:

- **whisper_segments**: Word-level transcription with timestamps
- **vocal_activity**: Fine-grained binary vocal detection (~100ms windows)
- **beat_map**: Beat positions in seconds
- **energy_curve**: RMS energy over time
- **tempo_bpm**: Detected tempo
- **sections**: Auto-detected musical sections with vocal density and energy

### Step 2.6: Climax Analysis

Run `scripts/analyze_climax_windows.py` on the same `song.mp3`:

```bash
python ~/.hermes/skills/creative/musical-mv-storyboard/scripts/analyze_climax_windows.py \
  song.mp3 \
  --output music_climax_analysis.json
```

Use the result before final shot planning:

- `top_4s_windows`: primary candidates for 3-5s lip-sync shorts
- `top_2s_windows`: candidates for beat cuts, flash hits, push-ins, and hero poses

Do not equate a larger visual with a stronger musical moment. If the highest 4s window has vocals, make it a short singer-led lip-sync shot; place wide shots and group dance before/after it.

### Step 2.7: Lip-Sync Phrase Map

Before any `lip_sync_closeup` is planned or generated, build `lip_sync_phrase_map.json`.

Purpose: make the vocal phrase, not the video segment, decide the lip-sync clip boundary.

Required checks:
- The phrase is one complete vocal sentence or musically complete line.
- It does not include the previous line tail, a mid-line pause plus another line, or the next line intro.
- The exported reference audio is clean PCM WAV.
- Whisper can transcribe the exported reference audio as the target lyric.
- If a 5s Seedance minimum is longer than the true vocal phrase, extra time belongs after the phrase as tail/emotion hold, not before the phrase as "preparation".

Minimal phrase object:

```json
{
  "phrase_id": "lip_phrase_05",
  "lyric_text": "我终于听见自己的光",
  "source_start": 24.38,
  "source_end": 29.38,
  "duration": 5.0,
  "reference_audio_wav": "audio/lip_phrases/lip_phrase_05.wav",
  "lyric_timing": [
    {"start": 0.00, "end": 1.80, "text": "我终于"},
    {"start": 1.80, "end": 2.44, "text": "听见"},
    {"start": 2.44, "end": 3.62, "text": "自己的"},
    {"start": 3.62, "end": 4.02, "text": "光"}
  ],
  "qc_status": "reference_audio_transcribes_correctly"
}
```

Director rule: a `lip_sync_closeup` in `shot_plan.director.json` must reference a `phrase_id`. If it does not, it is not ready for paid video generation.

### Realistic `audio_analysis.json` Excerpt

```json
{
  "whisper_segments": [
    {
      "start": 10.2,
      "end": 14.8,
      "text": "走在霓虹灯下我找不到方向",
      "words": [
        {"start": 10.2, "end": 10.7, "word": "走"},
        {"start": 10.7, "end": 11.1, "word": "在"},
        {"start": 11.1, "end": 11.6, "word": "霓"},
        {"start": 11.6, "end": 12.0, "word": "虹"},
        {"start": 12.0, "end": 12.5, "word": "灯"},
        {"start": 12.5, "end": 12.9, "word": "下"},
        {"start": 12.9, "end": 13.8, "word": "我"},
        {"start": 13.8, "end": 14.8, "word": "找不到方向"}
      ]
    },
    {
      "start": 42.0,
      "end": 47.5,
      "text": "你是我心中不灭的火",
      "words": [
        {"start": 42.0, "end": 42.4, "word": "你"},
        {"start": 42.4, "end": 42.8, "word": "是"},
        {"start": 42.8, "end": 43.5, "word": "我"},
        {"start": 43.5, "end": 44.0, "word": "心中"},
        {"start": 44.0, "end": 45.0, "word": "不灭的"},
        {"start": 45.0, "end": 47.5, "word": "火"}
      ]
    }
  ],
  "vocal_activity": [
    {"start": 0.0, "end": 0.8, "has_vocal": false},
    {"start": 0.8, "end": 1.6, "has_vocal": false},
    {"start": 1.6, "end": 2.4, "has_vocal": false},
    {"start": 2.4, "end": 3.2, "has_vocal": true},
    {"start": 3.2, "end": 4.0, "has_vocal": true},
    {"start": 4.0, "end": 4.8, "has_vocal": false},
    {"start": 4.8, "end": 5.6, "has_vocal": false},
    {"start": 5.6, "end": 6.4, "has_vocal": false},
    {"start": 6.4, "end": 7.2, "has_vocal": false},
    {"start": 7.2, "end": 8.0, "has_vocal": false},
    {"start": 8.0, "end": 8.8, "has_vocal": false},
    {"start": 8.8, "end": 9.6, "has_vocal": false},
    {"start": 9.6, "end": 10.4, "has_vocal": true},
    {"start": 10.4, "end": 11.2, "has_vocal": true},
    {"start": 11.2, "end": 12.0, "has_vocal": true},
    {"start": 12.0, "end": 12.8, "has_vocal": true},
    {"start": 12.8, "end": 13.6, "has_vocal": true},
    {"start": 13.6, "end": 14.4, "has_vocal": true},
    {"start": 14.4, "end": 15.2, "has_vocal": true},
    {"start": 15.2, "end": 16.0, "has_vocal": true}
  ],
  "beat_map": [0.47, 0.94, 1.41, 1.88, 2.35, 2.82, 3.29, 3.76, 4.23, 4.70],
  "energy_curve": {
    "timestamps": [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 5.0, 8.0, 10.0, 12.0, 15.0],
    "values": [0.12, 0.15, 0.18, 0.22, 0.20, 0.25, 0.35, 0.30, 0.15, 0.42, 0.48, 0.45]
  },
  "tempo_bpm": 128,
  "sections": [
    {"start": 0.0, "end": 10.0, "label": "intro", "vocal_density": 0.15, "avg_energy": 0.18},
    {"start": 10.0, "end": 28.0, "label": "verse", "vocal_density": 0.72, "avg_energy": 0.40},
    {"start": 28.0, "end": 42.0, "label": "pre-chorus", "vocal_density": 0.55, "avg_energy": 0.55},
    {"start": 42.0, "end": 62.0, "label": "chorus", "vocal_density": 0.82, "avg_energy": 0.78},
    {"start": 62.0, "end": 76.0, "label": "bridge", "vocal_density": 0.45, "avg_energy": 0.35},
    {"start": 76.0, "end": 90.0, "label": "chorus", "vocal_density": 0.85, "avg_energy": 0.82}
  ]
}
```

### How to Read This Data

| Section | vocal_density | avg_energy | Interpretation |
|---------|--------------|------------|----------------|
| intro (0–10s) | 0.15 | 0.18 | Mostly instrumental → `mv_broll` |
| verse (10–28s) | 0.72 | 0.40 | Dense vocal but moderate energy → `lip_sync_closeup` or `performance_medium` |
| pre-chorus (28–42s) | 0.55 | 0.55 | Mixed vocal, rising energy → `performance_medium` |
| chorus (42–62s) | 0.82 | 0.78 | Dense vocal + high energy → strong `lip_sync_closeup` candidate (select hero lines) |
| bridge (62–76s) | 0.45 | 0.35 | Sparse vocal, lower energy → `mv_broll` or `performance_medium` |
| final chorus (76–90s) | 0.85 | 0.82 | Peak density + peak energy → `lip_sync_closeup` for key lines, `dance_or_group` for rest |

---

## Step 3: Build Timeline

Run `scripts/build_music_timeline.py` using the section timestamps from `audio_analysis.json`.

### `music_timeline.json` Output

```json
{
  "duration": 90.0,
  "source_analysis": "audio_analysis.json",
  "timeline": [
    {"section_index": 1, "section": "intro", "start": 0.0, "end": 10.0, "lyrics": []},
    {"section_index": 2, "section": "verse", "start": 10.0, "end": 28.0, "lyrics": ["走在霓虹灯下我找不到方向", "城市的灯光太亮让我迷茫", "直到你在人群中出现"]},
    {"section_index": 3, "section": "pre-chorus", "start": 28.0, "end": 42.0, "lyrics": ["心跳加速的感觉", "世界突然有了颜色"]},
    {"section_index": 4, "section": "chorus", "start": 42.0, "end": 62.0, "lyrics": ["你是我心中不灭的火", "燃烧着我的每一个梦", "无论多远我都跟着你走"]},
    {"section_index": 5, "section": "bridge", "start": 62.0, "end": 76.0, "lyrics": ["即使路途再遥远", "即使黑夜再漫长"]},
    {"section_index": 6, "section": "chorus", "start": 76.0, "end": 90.0, "lyrics": ["你是我心中不灭的火", "永远照亮我的天空"]}
  ]
}
```

Key difference from the old system: timestamps come from **audio analysis**, not line-count estimation.

---

## Step 4: Classify Shots

Run `scripts/classify_musical_shots.py` on `music_timeline.json`, cross-referencing `audio_analysis.json` for vocal density and energy.

### `shot_plan.json` Output (before director enrichment)

```json
{
  "duration": 90.0,
  "shots": [
    {
      "shot_id": "shot_01",
      "start": 0.0,
      "end": 10.0,
      "section": "intro",
      "shot_type": "mv_broll",
      "requires_exact_lip_sync": false,
      "lyrics": [],
      "director_intent": "",
      "visual_prompt": ""
    },
    {
      "shot_id": "shot_02",
      "start": 10.0,
      "end": 28.0,
      "section": "verse",
      "shot_type": "performance_medium",
      "requires_exact_lip_sync": false,
      "lyrics": ["走在霓虹灯下我找不到方向", "城市的灯光太亮让我迷茫", "直到你在人群中出现"],
      "director_intent": "",
      "visual_prompt": ""
    },
    {
      "shot_id": "shot_03",
      "start": 28.0,
      "end": 42.0,
      "section": "pre-chorus",
      "shot_type": "performance_medium",
      "requires_exact_lip_sync": false,
      "lyrics": ["心跳加速的感觉", "世界突然有了颜色"],
      "director_intent": "",
      "visual_prompt": ""
    },
    {
      "shot_id": "shot_04",
      "start": 42.0,
      "end": 50.0,
      "section": "chorus",
      "shot_type": "lip_sync_closeup",
      "requires_exact_lip_sync": true,
      "lyrics": ["你是我心中不灭的火", "燃烧着我的每一个梦"],
      "director_intent": "",
      "visual_prompt": ""
    },
    {
      "shot_id": "shot_05",
      "start": 50.0,
      "end": 62.0,
      "section": "chorus",
      "shot_type": "dance_or_group",
      "requires_exact_lip_sync": false,
      "lyrics": ["无论多远我都跟着你走"],
      "director_intent": "",
      "visual_prompt": ""
    },
    {
      "shot_id": "shot_06",
      "start": 62.0,
      "end": 76.0,
      "section": "bridge",
      "shot_type": "mv_broll",
      "requires_exact_lip_sync": false,
      "lyrics": ["即使路途再遥远", "即使黑夜再漫长"],
      "director_intent": "",
      "visual_prompt": ""
    },
    {
      "shot_id": "shot_07",
      "start": 76.0,
      "end": 84.0,
      "section": "chorus",
      "shot_type": "lip_sync_closeup",
      "requires_exact_lip_sync": true,
      "lyrics": ["你是我心中不灭的火"],
      "director_intent": "",
      "visual_prompt": ""
    },
    {
      "shot_id": "shot_08",
      "start": 84.0,
      "end": 90.0,
      "section": "chorus",
      "shot_type": "dance_or_group",
      "requires_exact_lip_sync": false,
      "lyrics": ["永远照亮我的天空"],
      "director_intent": "",
      "visual_prompt": ""
    }
  ]
}
```

### Classification Rationale

| Shot | Section | vocal_density | avg_energy | Classification |
|------|---------|--------------|------------|----------------|
| 01 | intro | 0.15 | 0.18 | `mv_broll` — sparse vocal, low energy, establishing |
| 02 | verse | 0.72 | 0.40 | `performance_medium` — dense vocal but moderate energy, walking/singing |
| 03 | pre-chorus | 0.55 | 0.55 | `performance_medium` — mixed vocal, building gestures |
| 04 | chorus | 0.82 | 0.78 | `lip_sync_closeup` — peak density + peak energy = hero line |
| 05 | chorus | 0.82 | 0.78 | `dance_or_group` — same section but second half shifts to dance |
| 06 | bridge | 0.45 | 0.35 | `mv_broll` — sparse vocal, low energy, visual rest |
| 07 | final chorus | 0.85 | 0.82 | `lip_sync_closeup` — title drop, final emotional peak |
| 08 | final chorus | 0.85 | 0.82 | `dance_or_group` — closing spectacle |

Note how the chorus is split into two shots (04+05, 07+08) — this alternates lip-sync with dance to maintain visual variety and pacing.

---

## Step 5: Director Storyboard

The director (human or LLM) fills in the creative briefs for each shot using the template from `references/director-template.md`. This is the creative core of the project.

For every peak or lip-sync shot, the director must also fill:

- `music_reason`: why this exact time window deserves attention
- `climax_window`: copied from `music_climax_analysis.json` when applicable
- `target_lip_sync_duration`: usually 3-4s, max 5s unless a longer generated shot has already been previewed and approved

The director must not replace a vocal climax with a random bigger visual. Wide spectacle, group dance, lightning, gold light, and resurrection shots are only valid when they support the identified music window.

See `director-template.md` for the full worked example of shots 01, 02, and 03.

---

## Step 5.5: Asset Review Gate

Before cinematic keyframes, create asset review images for any project with complex recurring assets:

- main character face / body / wardrobe states
- family or group members
- vehicles
- important props
- museum artifacts / creature cast / product cast
- locations that must remain recognizable

The asset review image is not a mood shot. It answers one question: **what does this asset look like?**

Asset review requirements:

- light neutral background, conservation studio / casting sheet / reference table look
- soft clear lighting, readable silhouette, enough space around the subject
- no dark MV atmosphere, no stage lighting, no smoke, no heavy shadows, no red lasers, no fantasy glow
- for antiques: real material age first, including patina, oxidation, chips, cracks, dust, faded pigment, old restoration marks
- for characters: face, hair, body type, wardrobe state and accessories must be inspectable

Only after the asset review is readable and accepted should the director create `cinematic_keyframe` images. Cinematic keyframes may use night lighting, dramatic contrast, movement, camera angle, effects, and MV atmosphere.

Preview rule: `preview.html` must show asset review before shot keyframes. If the page jumps straight to dark cinematic images, the gate is missing. When `edit_decision_qc.json` exists, preview must also show the recommended candidate and ranking before old/alternate versions.

---

## Step 6: Generate Video Prompts

Run `scripts/build_video_prompts.py` on the enriched `shot_plan.json`.

### `video_prompts.json` Output

```json
{
  "duration": 90.0,
  "prompts": [
    {
      "shot_id": "shot_01",
      "start": 0.0,
      "end": 10.0,
      "shot_type": "mv_broll",
      "requires_exact_lip_sync": false,
      "video_prompt": "10.0s music-video shot, neon cyberpunk stage. Section: intro. Shot type: mv_broll. Wide shot of empty concert stage, thick colored fog in cyan and magenta, LED panels glowing with abstract patterns, single spotlight illuminating center, slow dolly forward through fog, LED patterns slowly shifting, atmospheric and moody"
    },
    {
      "shot_id": "shot_04",
      "start": 42.0,
      "end": 50.0,
      "shot_type": "lip_sync_closeup",
      "requires_exact_lip_sync": true,
      "video_prompt": "8.0s music-video shot, neon cyberpunk stage. Section: chorus. Shot type: lip_sync_closeup. Slow push-in to medium close-up of young woman, golden warm light from left, singing the words '你是我心中不灭的火', mouth open mid-phrase, slight head tilt, wind gently moving her hair, eyes intense and focused, background lights pulsing"
    }
  ]
}
```

---

## Step 7: Production Pipeline

```
For each shot in shot_plan.json:

1. ASSET REVIEW GATE
   - If the shot uses recurring people, vehicles, props, museum artifacts, creatures, products, or costumes, first confirm the matching `asset_review` image.
   - Do not use dark cinematic mood images for this step.

2. GENERATE CINEMATIC KEYFRAME IMAGE
   - Use seedance_image_prompt with GPT-Image-2 / doubao after the asset review is accepted.
   - For every visual_duration_plan generation_unit, generate one single-scene cinematic keyframe. The keyframe is the actual first visual state of that micro-shot, not a design sheet.
   - Never send asset review sheets, prop cast sheets, contact sheets, or storyboard grids directly to Seedance. They are upstream references only.
   - Upload to public URL (imgur)

3. SEEDANCE I2V
   - Submit image URL + seedance_video_prompt to APImart
   - Real-person / face / singer / lip-sync shots default to `doubao-seedance-2.0-face`, `480p`, `9:16`, `generate_audio=false`
   - Non-human / object / landscape / abstract B-roll shots default to `doubao-seedance-2.0`, `480p`, `9:16`, `generate_audio=false`
   - `fast` models are only for low-cost direction tests; do not use fast for candidate final clips by default
   - Use `image_urls` with public URLs; do not assume Seedance accepts local file paths or base64
   - For lip-sync shots, generate the provider minimum if needed, but plan to use only the best 3-4s in the EDL
   - For long B-roll/dance shots, split into 5-15s chunks only when the timeline requires it
   - Output: scene_XX.mp4

4. EDIT DECISION QC
   - If there is only one usable candidate, record the reason in the EDL notes.
   - If there are 2+ trims or 2+ generated versions, create `edit_decision_qc.json` from `templates/edit_decision_qc.example.json`.
   - Run `scripts/score_edit_candidates.py edit_decision_qc.json --write`.
   - Use the highest-scored non-blocked `recommended_candidate` as the preview/EDL default.
   - Do not pick a shorter version only because it hides one defect if it damages music build, story completeness, or handoff energy.

5. PLACE ON TIMELINE
   - Each clip goes at its start time from shot_plan.json
   - Fill gaps with black frames or last-frame hold
   - If the clip came from `edit_decision_qc.json`, add `edit_decision_candidate_id` to the EDL entry.

6. FINAL EDIT GATE
   - Before final ffmpeg concat, run `scripts/prepare_final_edit.py`.
   - The script must pass before delivery. It fails if EDL references the wrong candidate, lacks a recommended candidate, or cannot prove the recommended source.

   ```bash
   python ~/.hermes/skills/creative/musical-mv-storyboard/scripts/prepare_final_edit.py \
     --discover-root . \
     --edl videos/final/final_edl.json \
     --output videos/final/final_edit_gate_report.json \
     --require-edl
   ```

7. OPTIONAL WAV2LIP (only when exact lip-sync is required)
   - Extract matching audio segment: song.mp3 from {start}s to {end}s
   - Run Wav2Lip on scene_XX.mp4 with audio segment only if Seedance approximate lip-sync is not enough
   - Output: scene_XX_lipsync.mp4

8. FFMPEG CONCAT
   - All clips → concat demuxer → master timeline
   - Mix in original song.mp3 as audio track
   - Output: final_output.mp4
```

---

## File Manifest

| File | Produced By | Consumed By |
|------|------------|-------------|
| `song.mp3` | ElevenLabs / user | analyze_audio.py |
| `audio_analysis.json` | analyze_audio.py | build_music_timeline.py, classify_musical_shots.py |
| `music_climax_analysis.json` | analyze_climax_windows.py | director planning, build_preview.py |
| `music_timeline.json` | build_music_timeline.py | classify_musical_shots.py |
| `shot_plan.json` | classify_musical_shots.py + director | build_video_prompts.py |
| `assets/asset_review/*` | director / image generator | asset identity gate, build_preview.py |
| `video_prompts.json` | build_video_prompts.py | Image + I2V generation |
| `preview.html` | build_preview.py | Human/agent QC gate |
| `scene_XX.mp4` | Seedance I2V | Wav2Lip, ffmpeg |
| `edit_decision_qc.json` | score_edit_candidates.py / director | build_preview.py via `--edit-decision-qc`, EDL selection |
| `*_edl.json` | ffmpeg/assembly script | final timeline source of truth |
| `final_edit_gate_report.json` | prepare_final_edit.py | delivery gate evidence |
| `*_contact.jpg` | ffmpeg/QC script | visual QC |
| `final_output.mp4` | ffmpeg | Delivery |
