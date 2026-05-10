---
name: musical-mv-storyboard
description: "音乐剧/MV导演规划 skill：music-first 的音乐视频制作流水线。从歌曲/歌词生成或导入，到 Whisper/能量/爆点分析、短对口型布点、导演分镜、关键帧、生视频、EDL/preview.html、ffmpeg 后期合成。适用于真人音乐剧、唱跳 MV、剧情 MV、AI 生成歌曲配视频。"
metadata:
  tags: [musical, MV, music video, lyrics, lip sync, 唱跳, 音乐剧]
  version: "2.4"
---

# Musical MV Storyboard

## Boundary

用于 music-first 的音乐视频项目。核心不是“把画面做大”，而是让画面、口型、剪辑点服务音乐。

五种镜头类型：
- `lip_sync_closeup`：清晰面部，对口型，嘴型匹配该时间段歌词
- `performance_medium`：歌手可见，允许大致嘴部动作，不要求逐字同步
- `dance_or_group`：群舞/编舞，不需要口型
- `mv_broll`：象征性画面、风景、道具、氛围，无口型
- `transition`：视觉过渡，无口型

如果用户要求逐帧精确口型，分镜完成后再调用 `mv-lip-sync-pipeline`。Seedance 的“口型”只能做到视觉上像在唱，不能保证逐字同步。

## Non-Negotiable Rules

- **先分析音乐爆点，再设计镜头**。不允许先平均切 12 个镜头再硬塞画面。
- **短对口型优先**：单个对口型目标 `3-4s`，通常不超过 `5s`。7-8s 只有在实际成片验证很好时才保留。
- **爆点有人声时，优先给女主/主唱短对口型**，大远景/群舞放在前后承接。
- **画面变大不等于音乐更炸**。雷电、金光、群舞必须踩在 `music_climax_analysis.json` 的爆点窗口上才成立。
- **APImart Seedance MV 参数**：`image_urls`、`size: "9:16"`、`resolution: "480p"`、`generate_audio: false`。
- **最终音频只用主歌曲**：视频模型不要生成 BGM/独立音频；合成时 `-map 0:v -map 1:a` 覆盖完整 `song.mp3`。
- **主歌曲时间轴是母版**：一旦 `song.mp3`、Whisper 时间戳、EDL 开始使用，后期只能把画面贴到音乐上，不能移动音乐去适配画面。
- **已确认口型 offset 必须冻结**：A/B/C 小样确认后，在 EDL 记录 `confirmed_variant` 和 `lip_sync_offset_seconds`；封面、字幕、特效、重合成不得改变这些窗口。
- **封面/标题卡默认 replace，不默认 insert**：MV 成片加封面时，默认替换原片前 N 秒，保持全片时间轴不变；若选择插入 N 秒，必须重算所有 EDL、字幕和口型窗口。
- **最终口型 proof 门禁**：任何最终导出后，必须从最终视频本身导出每个已确认口型窗口的 proof clip，不能只相信中间小样。
- **付费视频串行提交**：一个任务完成并确认可用后再提交下一个；不要重提已完成任务。
- **持续维护 `preview.html`**：任何关键帧、视频、EDL、最终预览变更后，用户刷新页面应看到最新状态。

## Core Workflow

### Step 1: Lock the Music

- 使用用户提供的音频，或用 `scripts/generate_elevenlabs_song.py` 生成 vocal song。
- 明确主唱性别、语言、歌词、时长、BPM/风格目标。
- Output: `song.mp3`、`song.json`、`song.prompt.txt`。

### Step 2: Audio + Lyrics Analysis

运行：

```bash
python ~/.hermes/skills/creative/musical-mv-storyboard/scripts/analyze_audio.py \
  song.mp3 \
  --language en \
  --output audio_analysis.json
```

检查：
- Whisper 歌词时间戳是否可用
- 人声性别是否和主角设计一致
- 自动段落 `sections` 是否合理；不合理必须人工修正

Output: `audio_analysis.json`。

### Step 2.6: Climax Windows（必须）

运行：

```bash
python ~/.hermes/skills/creative/musical-mv-storyboard/scripts/analyze_climax_windows.py \
  song.mp3 \
  --output music_climax_analysis.json
```

用途：
- `top_4s_windows`：决定 3-5s 短对口型落点
- `top_2s_windows`：决定闪白、鼓点硬切、强推拉、hero pose 落点
- 爆点评分结合能量和 onset 起跳；不是凭感觉判断

必须把爆点窗口和 Whisper 歌词对齐后，才决定哪些地方做 `lip_sync_closeup`。

### Step 3: Timeline + Initial Classification

运行：

```bash
python ~/.hermes/skills/creative/musical-mv-storyboard/scripts/build_music_timeline.py \
  audio_analysis.json \
  --output music_timeline.json

python ~/.hermes/skills/creative/musical-mv-storyboard/scripts/classify_musical_shots.py \
  music_timeline.json \
  --output shot_plan.auto.json
```

注意：`classify_musical_shots.py` 只能给初稿。最终 `shot_plan` 必须由 LLM/导演基于 `music_climax_analysis.json` 二次修正：
- 对口型只选歌词强、音乐强、画面需要角色唱出来的位置
- 不要把整段 chorus/final chorus 直接做成长口型镜头
- 生成服务最低 5s 时，成片仍可只取最有效 3-4s
- `build_video_prompts.py` 对 `lip_sync_closeup` 默认只给 Seedance 5s，再由 EDL 裁出目标 3-4s
- B-Roll/群舞负责填缝和承接，不要抢主唱爆点

### Step 3.5: Preview Page Gate

在生视频之前必须生成或维护 `preview.html`。页面至少包含：
- 顶部“当前推荐观看版本 / 当前检查顺序”，不要把资料一股脑平铺
- 问题段小样、当前抽帧、最终成片放第一屏
- 全曲人声地图、歌词时间轴、2s/4s 爆点窗口
- 分镜表、镜头类型、短对口型目标时长、音乐理由
- 关键帧图、已生成视频、QC 抽帧、最终预览
- EDL/剪辑时间线
- 旧版本、技术分析、长 prompt 默认折叠

不要等用户提醒才更新。每次改文件后都要重建预览页。

推荐使用：

```bash
python ~/.hermes/skills/creative/musical-mv-storyboard/scripts/build_preview.py \
  shot_plan.director.json \
  --prompts video_prompts.json \
  --climax music_climax_analysis.json \
  --keyframe-dir assets/keyframes \
  --video-dir videos/seedance \
  --qc-video-dir videos/seedance/qc_audio \
  --final-video videos/final/final_output.mp4 \
  --focus-video videos/final/issue_excerpt.mp4 \
  --contact-sheet videos/final/final_contact.jpg \
  --edl videos/final/final_edl.json \
  --output previews/preview.html
```

预览页的职责是“导演看版 / 付费生成前门禁”，不是数据库 dump。第一屏必须回答：现在看哪个版本、哪个片段有问题、下一步该确认什么。

### Step 4: Director Storyboard

对每个镜头填写：

| 字段 | 说明 |
|------|------|
| `director_intent` | 这个镜头为什么存在，服务哪个音乐/剧情节点 |
| `visual_description` | 观众看到什么 |
| `camera` | 景别、运动、角度 |
| `lighting` | 主光、色调、氛围 |
| `reference_style` | 视觉参考 |
| `lip_sync_notes` | 仅对口型：精确歌词、嘴部状态、时间窗口 |
| `music_reason` | 这个镜头对应的音乐理由：爆点、人声、起跳、承接或释放 |
| `climax_window` | 如果踩爆点，记录来自 `music_climax_analysis.json` 的窗口 |
| `target_lip_sync_duration` | 对口型目标成片时长，默认 `3-4s` |
| `seedance_image_prompt` | 关键帧生图 prompt |
| `seedance_video_prompt` | I2V motion prompt |

导演判断优先级：
1. 是否踩中音乐爆点
2. 是否有人声和可唱出的歌词
3. 主唱脸和嘴是否是主体
4. 大场面是否服务音乐，而不是炫技
5. 镜头长度是否足够短、足够准

### Step 5: Keyframes + Video Generation

推荐顺序：
1. 生主角/角色参考图
2. 生每个镜头关键帧
3. 更新 `preview.html`
4. 用户或 Agent QC 后，再串行提交 Seedance 视频

Seedance 规则：
- 真人剧/真人音乐剧优先 `doubao-seedance-2.0-fast-face`
- MV 预览优先 `480p` 控成本；需要最终清晰度再考虑更高方案
- `generate_audio=false`
- `image_urls` 传参考图 URL，不要默认 base64 给 Seedance
- 每个视频 prompt 必须写清楚“不要自带音乐/BGM，最终会后期叠加完整歌曲”
- 对口型镜头的 `seedance_video_prompt` 必须包含该窗口的具体歌词；不能只写 “she sings”

### Step 6: Post-Production

合成规则：
- 所有片段统一规格、无音频轨
- lip-sync 附近硬切，不用 xfade/crossfade
- 最终单独混入 `song.mp3`
- 生成 `*_edl.json` 记录 source、timeline_start、timeline_end、duration、用途
- 生成 `*_contact.jpg` 抽帧总览
- 验证最终视频/音频时长

音频时间轴规则：
- `song.mp3` 是 immutable master timeline。正片、封面、字幕、HyperFrames/React overlay 都必须对齐它。
- A/B/C 对口型小样确认后，把结果写入 EDL，例如 `confirmed_variant: "C"`、`lip_sync_offset_seconds: 0.50`。
- 后期改封面、字幕、调色、特效时，不能改变 `timeline_start`、`timeline_end` 和 `lip_sync_offset_seconds`。
- 封面/标题卡默认用 `replace first N seconds`：封面占用 0-N 秒，后面接原片 N 秒后的内容，总时长不增加。
- 只有明确需要片头新增时才用 `insert N seconds`；一旦 insert，必须整体重算 EDL、字幕、口型 proof 时间点。
- 每次最终导出后，从最终成片导出所有口型 proof clips，并放进 `preview.html` 第一屏或“口型复查”区域。

ffmpeg 原则：

```bash
ffmpeg -y -i final_silent.mp4 -i song.mp3 \
  -map 0:v -map 1:a \
  -c:v copy -c:a aac -b:a 192k \
  -shortest final_complete.mp4
```

## Required Outputs

| 文件 | 说明 |
|------|------|
| `song.mp3` | 主歌曲 |
| `audio_analysis.json` | Whisper + beat/energy 分析 |
| `music_climax_analysis.json` | 2s/4s 音乐爆点窗口 |
| `music_timeline.json` | 段落化时间线 |
| `shot_plan.auto.json` | 脚本初稿 |
| `shot_plan.director.json` | LLM/导演修正后的最终分镜 |
| `video_prompts.json` | 生图/生视频 prompts |
| `preview.html` | 可视化项目预览 |
| `*_edl.json` | 最终剪辑时间线 source of truth |
| `*_contact.jpg` | QC 抽帧总览 |
| `lipsync_proof/*.mp4` | 从最终成片导出的已确认口型窗口证明片段 |
| `final_output.mp4` | 最终视频 |

## Music Generation

通过 ElevenLabs 生成 vocal musical song：

```bash
python ~/.hermes/skills/creative/musical-mv-storyboard/scripts/generate_elevenlabs_song.py \
  --style "Cleopatra ancient Egyptian queen musical scene, 130 BPM, heavy sub bass, tribal drums, orchestral explosions, guzheng plucks, electric guitar riffs, dark choir, theatrical dance tension" \
  --vocal "Powerful clear English female lead vocal as Cleopatra, low male mummy chant responses, intelligible lyrics" \
  --arrangement "0-10s ritual chant build, 10-28s verse, 28-42s pre-chorus rise, 42-62s explosive chorus/drop, 62-76s bridge, 76-90s final chorus climax" \
  --lyrics-file /path/to/lyrics.txt \
  --duration-ms 90000 \
  --output /path/to/song.mp3
```

脚本从 `~/.hermes/skills/shared-lib/config.yaml` 的 `ElevenLabs.api_key` 读取凭据，或使用 `ELEVENLABS_API_KEY` / `XI_API_KEY`。

## Integration With Other Skills

| Skill | 用途 |
|-------|------|
| `seedance-i2v` | APImart/Seedance I2V 生成 |
| `mv-lip-sync-pipeline` | Wav2Lip 精确口型 |
| `image-generator` / `gpt-image` | 关键帧生图 |
| `ffmpeg-video-concat` | 后期合成 |

## References

- `references/lip-sync-policy.md`：选择性短对口型策略
- `references/director-template.md`：结构化分镜模板
- `references/prompt-craft.md`：视频 prompt 写法
- `references/shot-types.md`：镜头类型定义
- `references/workflow.md`：端到端 workflow 示例

## Scripts

| 脚本 | 功能 |
|------|------|
| `scripts/analyze_audio.py` | Whisper 转录 + librosa beat/energy 分析 |
| `scripts/analyze_climax_windows.py` | 轻量爆点窗口分析 |
| `scripts/build_music_timeline.py` | 从 audio_analysis.json 构建时间线 |
| `scripts/classify_musical_shots.py` | 基于音频数据的初步镜头分类 |
| `scripts/build_video_prompts.py` | 从 shot plan 生成 creative prompts |
| `scripts/build_preview.py` | 生成 preview.html |
| `scripts/generate_elevenlabs_song.py` | ElevenLabs 音乐生成 |

## Blood Lessons

- 不做 `music_climax_analysis.json` 就会把爆点放错，画面再大也不成立。
- 对口型不是越长越好。短、准、踩点，比 7-8s 长口型更可信。
- 好的完整对口型镜头可以保留，但必须来自实际成片验证。
- 大场面必须匹配音乐。`shot_11_v2` 这类“画面更大但不踩音乐爆点”的镜头不能替代真正爆点。
- 在强人声爆点前可以加 3s 左右的半对口型桥段，把观众带入主对口型镜头。
- 用户说“爆点不对”时，先查音乐窗口和 EDL，不要先重生图/视频。
- 合成问题优先修 EDL/ffmpeg，不要重新烧 Seedance。
- 封面、标题、字幕、特效是后期层，不得破坏已锁定的歌曲时间轴。封面默认替换前 N 秒，不插入到正片前。
- A/B/C 已确认的口型窗口必须从最终成片导出 proof clips 复查；如果 proof 坏了，先查时间轴是否被后期移动。
- 版本命名要清楚：`v1`、`v2_replace02_11`、`v3_lipsync_climax` 这类命名能避免误用旧片段。
