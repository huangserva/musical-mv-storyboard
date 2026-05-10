# Audio Lock Policy

The song or final narration track is the master timeline. Once lip-sync windows or voice timing are approved, every later edit must preserve that timeline unless the EDL is intentionally recalculated.

## Timeline Contract

Every final project should have one source of truth:

```json
{
  "master_audio": "audio/song.mp3",
  "timeline_origin": 0.0,
  "duration": 88.10,
  "clips": [
    {
      "id": "cover_01",
      "type": "cover",
      "cover_mode": "replace",
      "timeline_start": 0.0,
      "timeline_end": 2.0,
      "source_start": 0.0,
      "source_end": 2.0
    },
    {
      "id": "shot_04",
      "type": "lip_sync_closeup",
      "source": "videos/seedance/shot_04.mp4",
      "timeline_start": 31.92,
      "timeline_end": 36.38,
      "lyric_start": 32.42,
      "confirmed_variant": "C",
      "lip_sync_offset_seconds": 0.50,
      "proof_required": true,
      "proof_path": "videos/final/lipsync_proof/shot04_final_proof.mp4"
    }
  ]
}
```

## Cover / Title Card Rule

Default: `replace`.

`replace` means the cover occupies the first N seconds of the same master timeline. The final duration does not increase, and the main video resumes from original time N.

`insert` means the cover adds new time before the original video. This shifts every later visual, subtitle, and lip-sync window. Only use `insert` when the user explicitly wants a longer intro and the whole EDL is recalculated.

File naming must be explicit:
- Good: `final_cover_replace_2s_lipsync_ok.mp4`
- Risky: `final_with_cover_v1.mp4`
- If intentional insert: `final_cover_insert_2s_edl_recalculated.mp4`

## Confirmed Lip-Sync Rule

After A/B/C audition approval:

```text
timeline_start = lyric_start - lip_sync_offset_seconds
```

This relationship must not change during:
- cover/title card edits
- subtitle rendering
- HyperFrames / React overlays
- color grading
- final re-encoding
- contact sheet generation

If a final export looks wrong, check EDL timing before regenerating video.

## Required Gates

Before final delivery:

1. Validate EDL structure.
2. Validate final video duration against EDL duration.
3. Validate every confirmed lip-sync offset.
4. Export proof clips from the final video itself.
5. Put the final video and proof clips in `preview.html`.
6. Mark bad old versions as deprecated.

## Failure Patterns

| Symptom | Likely Cause | Correct Fix |
|---|---|---|
| All lip-sync windows are off by the same amount | Cover/title card was inserted | Rebuild as replace, or recalculate EDL |
| Only one lip-sync shot is off | Wrong `lip_sync_offset_seconds` or bad source trim | Adjust that EDL entry |
| Subtitles drift but mouth is correct | Subtitle timebase changed | Fix subtitle timing only |
| Music starts correctly but video starts late | Visual concat added gap | Fix concat/trim |
| Good A/B/C samples but bad final | Final export changed timeline | Validate audio lock and proof clips |

