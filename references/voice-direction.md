# Voice Direction

V2 adds a voice-director layer. The goal is not "generate a voice", but to direct a performance that matches the music, visuals, and emotional arc.

## Core Rule

Do not send plain narration or lyrics directly to a TTS/vocal model for long-form output. First create a `voice_director_plan.json`, audition the strongest 15-20 seconds, then freeze the accepted voice template.

## `voice_director_plan.json`

Recommended structure:

```json
{
  "project_title": "献给全世界母亲",
  "master_audio": "audio/song.mp3",
  "language": "zh",
  "voice_goal": "warm, human, emotional but not theatrical",
  "reference_voice": {
    "path": "audio/reference.wav",
    "notes": "soft adult female, natural breath, not announcer style"
  },
  "global_delivery": {
    "pace": "natural, with visible slowdowns on emotional lines",
    "emotion_range": "restrained verse, lifted chorus, warm final resolve",
    "avoid": ["flat reading", "AI announcer cadence", "over-acted crying"]
  },
  "segments": [
    {
      "id": "voice_01",
      "start": 0.0,
      "end": 18.0,
      "text": "她不是背景，她是光。",
      "visual_context": "mothers in different countries waking before sunrise",
      "performance_intent": "open softly, like a private dedication",
      "emotion": "tender, grateful, slightly restrained",
      "pace": "slow opening, natural middle, hold final word",
      "pauses": [
        {"after": "背景", "duration": 0.35, "reason": "let the sentence breathe"}
      ],
      "emphasis": ["不是", "光"],
      "breath": "small inhale before the first sentence",
      "volume_shape": "gentle rise, no sudden jumps",
      "audition_required": true,
      "audition_variants": ["A_restrained", "B_emotional", "C_cinematic"]
    }
  ]
}
```

## A/B/C Audition Pattern

Use the strongest 15-20 seconds first. Do not generate the full voice until this is accepted.

| Variant | Direction | When To Use |
|---|---|---|
| `A_restrained` | calm, intimate, minimal acting | documentary / memory vlog |
| `B_emotional` | warmer, more dynamic, clearer pauses | emotional MV / tribute |
| `C_cinematic` | larger performance, stronger rise and release | trailer / musical / climax |

After the user confirms a version, write the accepted settings into the project:

```json
{
  "accepted_voice_template": {
    "variant": "B_emotional",
    "model": "provider/model-name",
    "reference_voice": "audio/reference.wav",
    "prompt_style": "warm, human, emotional but controlled",
    "pace": "natural with intentional pauses",
    "post_processing": "eq_compress_ducking_v1"
  }
}
```

## Performance Tags

Use concrete direction, not vague adjectives.

Good:
- "pause 0.4s after this line, as if holding back emotion"
- "slightly faster on the travel montage, then slow down on the final sentence"
- "lift the word `光`, but do not shout"
- "small breath before the chorus line"

Bad:
- "more emotional"
- "read beautifully"
- "sound real"
- "make it touching"

## Long-Form Generation

- Prefer one pass for a consistent voice when the model can handle it.
- If splitting is required, split by emotional chapters, not sentence-by-sentence.
- Reuse the accepted reference voice and exact delivery template for every chunk.
- After stitching, run a consistency check for timbre drift, loudness jumps, and unnatural pauses.

## Acceptance Checklist

- The first 5 seconds do not sound like an AI announcer.
- Key words have intentional emphasis.
- Pauses feel motivated by the scene.
- Emotion rises and falls with the music, not randomly.
- The voice still sounds like the same person after stitching.
- Final audio is reviewed inside the real video, not only as a standalone file.

