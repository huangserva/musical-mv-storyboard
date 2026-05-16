# Prompt Craft Guide

How to write effective video prompts for Seedance I2V generation across all five shot types.

---

## Core Principles

### 1. Be Specific, Not Generic

Bad: "nice lighting"
Good: "golden hour backlight through sheer curtains, dust particles floating in warm amber beams"

Bad: "dramatic lighting"
Good: "single overhead spotlight in otherwise dark room, hard shadow on floor, cold blue fill from window"

The image prompt defines the scene; the video prompt defines the motion. Both must be concrete and visual.

### 2. Motion Comes First

In the video prompt, the FIRST things you describe should be WHAT moves, HOW it moves, and at WHAT pace. Seedance I2V is image-to-video — the image already establishes the scene. The prompt tells the model what to *do* with it.

Good: "Wind gently lifts her hair, camera slowly pushes in, dust particles drift left to right"
Bad: "A beautiful emotional moment in a music video"

### 3. Seedance I2V Is NOT Text-to-Video

The uploaded keyframe image defines:
- Who/what is in the scene
- Where they are
- The color palette and lighting
- The composition and framing

Therefore the uploaded image must already be a single cinematic shot frame. Do not upload asset review sheets, prop cast sheets, character design sheets, contact sheets, storyboard grids, or multi-panel collages as the main Seedance image. If the image is a sheet/grid, Seedance will usually animate the sheet/grid itself, even if the prompt says not to show it.

The video prompt should NOT redundantly describe these. It should describe:
- Movement (of subjects, camera, elements)
- Timing and pace (slow, fast, sudden, gradual)
- Interactions (wind on hair, rain on surface, light shifting)

If you find yourself describing the scene setup in the video prompt, move that to the image prompt instead.

### 4. Lip-Sync Prompts Focus on Mouth + Body Language

For `lip_sync_closeup` shots, the video prompt should describe:
- Mouth state (open, closed, mid-word, smiling)
- Subtle body language (head tilt, slight shoulder movement, eye direction)
- Very restrained camera movement (slow push or static)

Do NOT describe the story, the lyrics' meaning, or the emotional context — those are in the director's notes.

### 5. Match Energy to Music Section

| Section | Energy | Prompt Approach |
|---------|--------|-----------------|
| Intro / verse (low) | Calm | Slow movements, gentle camera, ambient motion (dust, fog, wind) |
| Pre-chorus (rising) | Building | Accelerating movement, camera push-in, gestures growing larger |
| Chorus / drop (peak) | High | Dynamic motion, wider gestures, sharp or sustained movement |
| Bridge / outro (falling) | Settling | Decelerating, pull-back camera, fading motion |

**Important:** Low energy ≠ static. Even quiet shots should have subtle motion — breathing, dust, light shifting, gentle wind. Static footage feels dead.

**Important:** High energy ≠ chaos. Describe purposeful, rhythmic movement — not random shaking.

---

## Per-Shot-Type Prompt Patterns

### `lip_sync_closeup`

**Image prompt:** Describe the frozen moment — face, expression, lighting, background.
- Face angle, expression, emotion readable on face
- Lighting direction and quality on the face
- Background context (blurred is fine)

**Video prompt:** Describe mouth state + subtle body motion + restrained camera.
- Include the exact lyric phrase being sung
- Describe mouth: "mouth open mid-phrase", "lips closing on final word"
- Body: "slight head tilt", "eyebrows raised", "shoulders subtly shifting"
- Camera: "slow push-in" or "static" — never whip pan or fast movement
- Ambient: "wind gently moving hair", "light dust particles drifting"

**Example:**
```
Image: Medium close-up of young woman, warm golden light from left,
        singing expression with mouth slightly open, wind lifting hair,
        blurred stage lights in background, cinematic portrait quality

Video: Slow push-in to medium close-up of young woman, warm golden light
        from left, singing the words '你是我心中不灭的火', mouth open
        mid-phrase, slight head tilt on last word, wind gently moving her
        hair, eyes intense and focused, very subtle shoulder movement
```

---

### `performance_medium`

**Image prompt:** Describe the character, their pose, and the environment.
- Body visible from roughly waist up
- Environment contributes to mood (location, weather, architecture)
- Costume, props, and posture are visible

**Video prompt:** Describe body language + movement through space.
- Walking, gesturing, turning, reaching
- Camera can track, dolly, or orbit — more freedom than closeup
- Interaction with environment (hand on wall, stepping through door, rain falling)
- Rough mouth motion is fine — "mouth moving in song"

**Example:**
```
Image: Medium shot of woman in silver outfit walking through neon-lit
        corridor, LED panels glowing cyan and magenta, rain visible
        through glass wall, one hand trailing along wall, confident stride

Video: Medium shot, woman walking confidently forward through neon corridor,
        one hand trailing along LED wall, rain falling outside glass panel,
        camera tracking beside her at walking pace, colors shifting on LED
        panels as she passes, mouth moving in song, occasional expressive
        hand gesture
```

---

### `dance_or_group`

**Image prompt:** Describe the formation, the energy, the space.
- Group formation visible (line, V-shape, circle, etc.)
- Stage or performance space is clear
- Energy should be readable in the pose — mid-move, dynamic

**Video prompt:** Describe the choreography pattern and energy.
- What movement: "sharp arm movements on beat", "fluid body wave", "synchronized kick"
- Group dynamics: "V-formation holding", "dancers spreading outward", "couple spinning"
- Energy matching: staccato for fast beats, sustained for soaring vocals
- Camera: can be dynamic — low angle, crane, orbit, but should follow the energy
- Environmental motion: lights sweeping, confetti falling, smoke rolling

**Example:**
```
Image: Wide shot of five dancers in V-formation on concert stage, mid-dance
        pose with sharp arm extension, colored laser lights sweeping, LED
        backdrop, smoke on stage floor, dynamic energy, low angle perspective

Video: Wide shot, five dancers in V-formation, explosive synchronized
        choreography, sharp arm movements on beat, then fluid body wave
        through formation, concert stage with colored laser lights sweeping,
        low angle looking up, smoke rolling across stage floor, pulsing
        energy matching the beat
```

---

### `mv_broll`

**Image prompt:** Describe the visual — mood, color, composition.
- Atmosphere and palette are primary
- Can be landscape, objects, weather, architecture, abstract
- Strong composition — this is a "photograph" moment

**Video prompt:** Describe ambient motion and atmospheric changes.
- Slow, contemplative movement — "slow aerial descent", "gentle pan", "clouds drifting"
- Natural motion: rain, wind, fire, water, fog, light shifting
- Color or light changes: "first light breaking through clouds", "neon signs flickering"
- The motion should feel immersive, not rushed

**Example:**
```
Image: Aerial view of misty mountain lake at dawn, first light breaking
        through clouds, single heron on still water, cool blue palette
        with warm amber horizon, ethereal and vast, fine art photography

Video: Slow aerial descent over misty mountain lake at dawn, first light
        slowly breaking through cloud layer, single heron taking flight
        from water surface, cool blue mist parting to reveal warm amber
        horizon, ethereal and vast, gentle breathing pace
```

---

### `transition`

**Image prompt:** Usually not needed (transitions are often generated from adjacent shots or very simple). If needed, describe the endpoint state.

**Video prompt:** Describe the movement that creates the bridge.
- Keep it focused on ONE clear motion idea
- Duration: 0.5–2s
- Movement types: wipe, pan, morph, dissolve, flash, match cut

**Example:**
```
Video: Whip pan from dark interior through open door into blazing bright
        desert, motion blur, lens flare, 1 second duration
```

Other transition patterns:
- "Smoke fills frame from bottom up, then clears to reveal new scene"
- "Match cut — falling rose petal in close-up becomes red dress fabric"
- "White flash on beat, brief, then pull back to reveal concert crowd"
- "Silhouette of figure walks toward camera, shadow grows to fill frame, cuts to new scene"

---

## Anti-Patterns — Things That Don't Work

| ❌ Bad Prompt | Why It Fails | ✅ Better Version |
|---|---|---|
| "singing beautifully" | Too vague — doesn't describe a visual | "mouth open mid-phrase, eyes closed, slight smile, golden side light" |
| "emotional moment" | Tells, doesn't show | "tear rolling down cheek, chin trembling, shallow depth of field, cool grey light" |
| "dramatic lighting" | Meaningless — what kind? | "single harsh spotlight from above, deep shadows, contrast ratio high" |
| "nice background" | No visual information | "blurred city lights at night, bokeh circles in warm amber and cool teal" |
| "dancer performs" | What dance? What energy? | "sharp arm pop on beat, then body roll down to floor, syncopated rhythm" |
| "camera moves" | How? Which direction? | "slow dolly forward, eye level, steady, 0.3x zoom over 5 seconds" |
| "looks sad" | Acting direction, not visual | "eyes downcast, shoulders hunched, hand pressed to forehead, dim warm interior light" |
| Lists 5+ visual elements | Seedance I2V works best with 1–2 clear motion ideas | Pick the 1–2 most important and describe them well |

## Prompt Length Guide

| Shot Type | Image Prompt | Video Prompt |
|-----------|-------------|--------------|
| lip_sync_closeup | 2–3 sentences (face + lighting + background) | 3–4 sentences (mouth + body + camera + ambient) |
| performance_medium | 2–3 sentences (character + environment + pose) | 3–4 sentences (movement + environment interaction + camera) |
| dance_or_group | 2–3 sentences (formation + energy + stage) | 3–4 sentences (choreography + dynamics + camera) |
| mv_broll | 2–3 sentences (scene + palette + composition) | 2–3 sentences (ambient motion + light/atmosphere change) |
| transition | 0–1 sentences (often not needed) | 1–2 sentences (single motion idea + duration) |
