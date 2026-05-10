# Post-Production Sound

AI voice and AI vocal output usually needs finishing. A good voice model can still sound cheap if it is pasted directly into the final video.

## Goals

- Speech/vocal is intelligible on phone speakers.
- Loudness is stable without crushing emotion.
- BGM supports the voice and ducks naturally.
- Cuts between voice chunks do not reveal timbre drift.
- The final mix feels like one piece, not exported assets stacked together.

## Standard Chain

Use this as a starting point, then adjust by ear.

1. Cleanup: trim clicks, remove long dead air, fade chunk boundaries.
2. EQ: high-pass below 70-100 Hz, reduce mud around 200-400 Hz if needed, add presence around 2-4 kHz carefully.
3. De-ess: tame harsh `s` and `sh` sounds.
4. Compression: light ratio, slow enough to keep emotion, fast enough to smooth jumps.
5. Loudness normalization: keep voice consistent across the MV.
6. BGM ducking: lower BGM under speech/vocal, release naturally after lines.
7. Final limiter: prevent clipping.

## Practical FFmpeg Starting Points

Normalize a narration file:

```bash
ffmpeg -y -i voice.wav \
  -af "highpass=f=80,acompressor=threshold=-18dB:ratio=2.2:attack=12:release=180,loudnorm=I=-16:TP=-1.5:LRA=9" \
  voice_processed.wav
```

Mix voice over BGM with basic ducking:

```bash
ffmpeg -y -i bgm.wav -i voice_processed.wav \
  -filter_complex "[0:a][1:a]sidechaincompress=threshold=0.08:ratio=6:attack=30:release=450[ducked];[ducked][1:a]amix=inputs=2:duration=longest:weights=0.75 1.0[a]" \
  -map "[a]" mix.wav
```

For a song-led MV, do not duck the master song unless there is separate narration. The song is the master audio.

## Voice Chunk Stitching

If voice generation must be split:

- Split by emotional section, not every sentence.
- Leave 200-500 ms room for natural breath and crossfade only between voice chunks, never across lip-sync video cuts.
- Match loudness of chunks before stitching.
- Check that the same speaker identity remains stable.

## Review In Video

Do not approve voice only from an audio player. The same voice can feel acceptable alone but wrong against the picture.

Review with:
- final or near-final visuals
- subtitles enabled
- phone speaker playback
- one pass at low volume for intelligibility
- one pass at normal volume for emotion

