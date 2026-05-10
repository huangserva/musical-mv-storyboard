# Director Template

Structured template for filling in each shot's creative brief in the MV storyboard. Use this for every shot in `shot_plan.json` after classification.

---

## Per-Shot Template

For each shot, fill in the following fields:

```markdown
## Shot {shot_id}: [{section}] {start}s - {end}s ({duration}s)

- **Shot Type:** {lip_sync_closeup | performance_medium | dance_or_group | mv_broll | transition}
- **Lip Sync Required:** {yes | no}
- **Director Intent:** WHY this shot exists in the musical arc. What emotional beat does it serve?
- **Music Reason:** Why this exact music window deserves this shot: vocal hook, energy rise, onset hit, bridge into chorus, or release.
- **Climax Window:** If used, copy the matching `music_climax_analysis.json` window. Otherwise write `N/A`.
- **Visual Description:** What the viewer sees — scene, character, action, mood.
- **Camera:** Shot size, movement, angle. (e.g. "medium close-up, slow push-in, eye level")
- **Lighting:** Key light direction, color palette, atmosphere. (e.g. "golden hour backlight, warm amber and cool blue, dusty haze")
- **Reference Style:** Visual reference — a specific film, MV, photographer, or aesthetic. (e.g. "Wong Kar-wai Chungking Express neon green")
- **Lip Sync Notes:** (Only for lip_sync_closeup) Exact lyric phrase being sung, mouth state expected.
- **Target Lip-Sync Duration:** (Only for lip_sync_closeup) Usually 3-4s, max 5s unless already verified in a final preview.
- **Seedance Image Prompt:** Prompt to generate the keyframe image. Describe the frozen moment.
- **Seedance Video Prompt:** Motion prompt for I2V generation. Describe what moves and how.
```

### Field Guidelines

| Field | Purpose | Tips |
|-------|---------|------|
| Director Intent | Justifies the shot's existence | Tie to emotional arc — "builds tension", "releases energy", "foreshadows theme" |
| Music Reason | Prevents random spectacle | Tie the shot to a climax window, lyric phrase, onset hit, or transition need |
| Climax Window | Anchors peak shots | Copy start/end/score from `music_climax_analysis.json` for peak shots |
| Visual Description | Concrete visual content | Be specific: "rain on taxi window" not "sad mood" |
| Camera | Technical camera direction | Size (wide/medium/close), movement (static/track/crane), angle (eye/low/high) |
| Lighting | Light and color design | Direction (front/side/back), palette (2-3 colors), quality (hard/soft) |
| Reference Style | Anchor the visual language | Use real references — helps both human collaborators and AI generation |
| Seedance Image Prompt | Generates keyframe | Describe the scene as a single photograph — no motion verbs |
| Seedance Video Prompt | Defines motion for I2V | Describe WHAT moves, HOW it moves, at WHAT pace. Always say no independent music/BGM. See `prompt-craft.md` |

---

## Musical Arc Mapping

Every MV follows an emotional journey. Map shots to this arc to ensure the visual rhythm mirrors the musical rhythm:

```
    BUILD          TENSION         RELEASE         RESOLUTION
    ──────        ────────        ───────         ──────────
    intro,        pre-chorus,     chorus/drop,    bridge,
    verse 1,      verse 2,        final chorus,   outro,
    setup         escalation      climax           denouement
```

### Arc-to-Shot Mapping

| Arc Phase | Typical Shot Types | Energy | Lip-Sync? |
|-----------|-------------------|--------|-----------|
| **Build** (intro, verse 1) | `mv_broll`, `performance_medium` | Low → rising | Maybe 1 closeup for hook |
| **Tension** (pre-chorus, verse 2) | `performance_medium`, `transition` | Rising | Optional — gesture shots |
| **Release** (chorus, drop) | `dance_or_group`, `lip_sync_closeup` | Peak | Yes for hero lines |
| **Resolution** (bridge, outro) | `mv_broll`, `lip_sync_closeup` (final line), `transition` | Falling → rest | Only for closing line |

### Key Principle

**The arc should breathe.** After a high-energy release, give the viewer visual rest with b-roll or a slower shot. After a quiet build, the release should feel earned. The shot type sequence should alternate between high-attention (closeup) and wide-expressive (dance/broll) to maintain engagement.

---

## Worked Example: Chinese Pop 唱跳 Song

**Song:** 《不灭的火》(Eternal Flame)
**Genre:** 华语流行舞曲 (Chinese Pop Dance)
**BPM:** 128
**Duration:** 90s
**Style:** Neon cyberpunk stage, cool blues and hot pinks, LED panels, backup dancers

### Arc Overview

```
0-10s   intro       BUILD        → mv_broll (establishing)
10-28s  verse       BUILD        → performance_medium (walk-and-sing)
28-42s  pre-chorus  TENSION      → performance_medium + transition (escalation)
42-62s  chorus      RELEASE      → dance_or_group + lip_sync_closeup (peak)
62-76s  bridge      RESOLUTION   → mv_broll + performance_medium (rest)
76-90s  final chorus RELEASE     → dance_or_group + lip_sync_closeup (final peak)
```

### Three Example Shots (Filled Template)

---

### Shot 01: [intro] 0.0s - 10.0s (10.0s)

- **Shot Type:** mv_broll
- **Lip Sync Required:** no
- **Director Intent:** Establish the world — an empty neon-lit stage waiting for the performer. Build anticipation. Cool, mysterious, atmospheric.
- **Visual Description:** Wide shot of an empty concert stage shrouded in colored fog. LED panels glow with abstract cyan and magenta patterns. A single spotlight slowly illuminates center stage. No people visible yet. Fog machines pulse gently.
- **Camera:** Wide shot, slow dolly forward toward center stage, eye level.
- **Lighting:** Cool cyan backlight from LED panels, single warm white spotlight from above center, magenta accent from stage-left. Moody, volumetric fog.
- **Reference Style:** K-pop MV intro aesthetic — BLACKPINK "How You Like That" stage reveal.
- **Lip Sync Notes:** N/A
- **Seedance Image Prompt:** Wide shot of empty dark concert stage, thick colored fog in cyan and magenta, LED panels glowing with abstract patterns on back wall, single bright spotlight illuminating center stage floor, volumetric haze, cinematic, 8K
- **Seedance Video Prompt:** Slow dolly forward through fog toward center stage, fog gently swirling and pulsing, LED panel patterns slowly shifting, spotlight brightening gradually, atmospheric and moody

---

### Shot 02: [verse] 10.0s - 28.0s (18.0s)

- **Shot Type:** performance_medium
- **Lip Sync Required:** no (rough mouth motion is fine)
- **Director Intent:** Introduce the performer and establish her presence. She moves through the space with confidence. The energy builds from controlled to assertive.
- **Visual Description:** Medium shot of a young woman in a sleek silver outfit walking through a neon-lit corridor of LED panels. She gestures expressively while singing, one hand running along the wall. Camera tracks beside her. Rain falls outside a glass wall to her left, reflecting neon colors. Backup dancers appear briefly in the background, out of focus.
- **Camera:** Medium shot, steady tracking shot beside the performer, eye level.
- **Lighting:** Neon cyan and pink sidelighting from LED corridor, rain reflections adding prismatic highlights, face lit by moving colored panels.
- **Reference Style:** Wong Kar-wai meets K-pop — Chungking Express neon green/blue palette but with stage fashion.
- **Lip Sync Notes:** N/A (performance_medium — rough mouth is acceptable)
- **Seedance Image Prompt:** Medium shot of young woman in sleek silver outfit walking through neon-lit corridor, LED panels glowing cyan and magenta on both sides, rain visible through glass wall on left reflecting colors, shallow depth of field, cinematic color grading, fashion photography style
- **Seedance Video Prompt:** Woman walking confidently forward through neon corridor, one hand trailing along LED wall, rain falling outside glass panel, camera tracking beside her at walking pace, colors shifting on LED panels as she passes

---

### Shot 03: [chorus] 42.0s - 46.0s (4.0s)

- **Shot Type:** lip_sync_closeup
- **Lip Sync Required:** yes
- **Music Reason:** Chorus title drop lands on a high-energy vocal hook, so this should be a short singer-led peak, not a long chorus coverage shot.
- **Climax Window:** 42.0s-46.0s, top 4s vocal/energy window.
- **Director Intent:** The emotional and visual climax of the first chorus. The viewer must see the singer's face and feel every word. This is the title drop — "你是我心中不灭的火" — the song's core message.
- **Visual Description:** Medium close-up of the lead singer, face filling frame, golden warm light from stage-left. She looks directly into camera with fierce determination. Background is blurred stage lights and backup dancers in motion. Wind machine blows her hair back. She sings the title line with full intensity.
- **Camera:** Medium close-up, slow push-in (very gradual), eye level, stable.
- **Lighting:** Warm golden key light from stage-left, cool cyan rim light from behind, magenta accent in blurred background. High contrast, glamorous.
- **Reference Style:** Beyoncé "Halo" — golden light closeup with wind-blown hair, divine and powerful.
- **Lip Sync Notes:** Exact phrase: "你是我心中不灭的火" (You are the eternal fire in my heart). Mouth should be clearly open mid-phrase, eyes intense, slight head tilt on "火" (fire).
- **Target Lip-Sync Duration:** 4.0s final timeline use, even if the generated Seedance clip is 5s.
- **Seedance Image Prompt:** Medium close-up of young Chinese woman's face looking directly into camera, fierce determined expression, golden warm light from left side, wind blowing hair back, blurred concert stage lights in background cyan and magenta, glamorous high-contrast lighting, fashion editorial quality, 8K
- **Seedance Video Prompt:** Very slow push-in toward woman's face, wind gently blowing hair, slight head tilt, she sings the exact phrase "你是我心中不灭的火", eyes intense and focused, background lights slowly pulsing, golden light warm and steady from left side. No independent music or BGM in the generated clip; final song will be added in post.

---
