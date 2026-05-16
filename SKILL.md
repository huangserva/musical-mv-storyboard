---
name: musical-mv-storyboard
description: "音乐剧/MV导演规划 skill：music-first 的音乐视频制作流水线。从歌曲/歌词生成或导入，到 Whisper/能量/爆点分析、短对口型布点、导演分镜、关键帧、生视频、EDL/preview.html、ffmpeg 后期合成。适用于真人音乐剧、唱跳 MV、剧情 MV、AI 生成歌曲配视频。"
metadata:
  tags: [musical, MV, music video, lyrics, lip sync, 唱跳, 音乐剧, voice direction]
  version: "2.11"
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
- **先写导演总谱，再写单 shot**。必须先把 `音乐结构 → 全片情绪曲线 → 视觉章节 → 每个 shot 的职责 → shot 之间的反差/承接` 写成 `director_score.json`，再进入生图/生视频。禁止只优化单个 shot 的炫酷程度。
- **先判断视觉时长，再写视频 prompt**。复杂 MV 段落必须写 `visual_duration_plan.json`：音乐窗口、戏剧 beat、最低可读时长、生成单位拆分。禁止把 4 个以上剧情 beat 塞进一个 15s Seedance 任务。
- **声音分段决定视频分段**。`lip_sync_closeup` 必须先绑定完整人声乐句，再决定视频时长、参考音频和 prompt；禁止用平均镜头段或任意时间片去切口型音频。
- **短对口型优先**：单个对口型目标 `3-4s`，通常不超过 `5s`。7-8s 只有在实际成片验证很好时才保留。
- **爆点有人声时，优先给女主/主唱短对口型**，大远景/群舞放在前后承接。
- **画面变大不等于音乐更炸**。雷电、金光、群舞必须踩在 `music_climax_analysis.json` 的爆点窗口上才成立。
- **APImart Seedance MV 参数**：`image_urls`、`size: "9:16"`、`resolution: "480p"`；真人/人脸默认 `doubao-seedance-2.0-face`，非真人/非人脸默认 `doubao-seedance-2.0`；`fast` 只允许低成本方向草测，不作为候选成片模型。最终成片默认不用视频模型音频，`generate_audio=true` 仅可用于单个口型 shot 的诊断 QC。
- **最终音频只用主歌曲**：视频模型不要生成 BGM/独立音频；合成时 `-map 0:v -map 1:a` 覆盖完整 `song.mp3`。
- **声音需要被导演**：TTS/演唱/旁白不能只丢文案给模型；先写 `voice_director_plan.json`，用 15-20s A/B/C 小样确认声音模板，再生成长音频。
- **主歌曲时间轴是母版**：一旦 `song.mp3`、Whisper 时间戳、EDL 开始使用，后期只能把画面贴到音乐上，不能移动音乐去适配画面。
- **服装连续性必须显式设计**：真人 MV 在生图前必须写 `wardrobe_plan.json`。每个可见人物 shot 必须有 `costume_state_id`；如果没有明确换装事件，相邻镜头服装和发型必须一致。MV 可以换装，但只能发生在音乐结构切换处，并且要在分镜和 preview 里交代。
- **资产确认图和正式镜头图必须分开**：`asset_review` 用浅背景、软光、清楚展示人物/物品/服装/车辆/道具，目的是确认“长什么样”；`cinematic_keyframe` 才允许夜景、暗光、舞台灯、运动和特效。禁止用黑暗气氛图替代资产确认图。
- **资产确认图不能直接喂给 Seedance**：`asset_review`、物品演员表、角色设定表、contact sheet、3x3/4x4 storyboard 都不是正式 I2V 首图。Seedance 输入必须是该 `generation_unit` 的单一 `cinematic_keyframe`，否则模型会把表格/拼贴本身动起来。
- **已确认口型 offset 必须冻结**：A/B/C 小样确认后，在 EDL 记录 `confirmed_variant` 和 `lip_sync_offset_seconds`；封面、字幕、特效、重合成不得改变这些窗口。
- **封面/标题卡默认 replace，不默认 insert**：MV 成片加封面时，默认替换原片前 N 秒，保持全片时间轴不变；若选择插入 N 秒，必须重算所有 EDL、字幕和口型窗口。
- **最终口型 proof 门禁**：任何最终导出后，必须从最终视频本身导出每个已确认口型窗口的 proof clip，不能只相信中间小样。
- **对口型必须跑硬门禁**：规划口型前跑 `scripts/lip_sync_gate.py --mode preflight`；最终合成前跑 `--mode final --require-proofs`。缺 `phrase_id`、clean WAV、offset 或 proof 时，不得声称口型已完成。
- **剪辑变动必须跑节奏审计**：任何删段、插段、压缩、顺延、封面 insert 或全片重排后，必须运行 `scripts/rhythm_audit.py`，把当前时间、源时间、歌词、beat、爆点和 shot 职责对齐落盘。
- **付费视频串行提交**：一个任务完成并确认可用后再提交下一个；不要重提已完成任务。
- **持续维护 `preview.html`**：任何关键帧、视频、EDL、最终预览变更后，用户刷新页面应看到最新状态。
- **剪辑选择必须多维评分并落盘**：推荐裁剪不能只优化单一缺陷。只要同一 shot 有 2 个以上候选版本，必须创建 `edit_decision_qc.json` 并运行 `scripts/score_edit_candidates.py --write`。主推荐必须来自最高分的非阻塞候选，而不是最保守或最新生成的版本。

## Core Workflow

### Step 1: Lock the Music

- 使用用户提供的音频，或用 `scripts/generate_elevenlabs_song.py` 生成 vocal song。
- 明确主唱性别、语言、歌词、时长、BPM/风格目标。
- Output: `song.mp3`、`song.json`、`song.prompt.txt`。

### Step 1.5: Voice Director（V2）

如果项目包含 TTS、旁白、演唱克隆或明显的人声表演，必须先写 `voice_director_plan.json`：
- 每句标注 `visual_context`、`performance_intent`、`emotion`、`pace`、`pauses`、`emphasis`、`breath`。
- 先挑最关键 15-20s 做 A/B/C 试音，不要一开始生成全片。
- 用户确认后冻结 `accepted_voice_template`，长音频复用同一参考声音、模型、提示词和后期链。
- 参见 `references/voice-direction.md`。

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

### Step 2.7: Lip-Sync Phrase Map（必须，口型镜头前置门禁）

在设计任何 `lip_sync_closeup` 之前，必须先从主歌曲里建立 `lip_sync_phrase_map.json`。

核心原则：**完整人声乐句先于视频镜头**。不能先把视频切成 5/6 秒，再从这些固定窗口里硬切音频。每个口型镜头只能绑定一个干净的完整乐句，不能混入上一句尾巴、停顿、下一句开头或纯伴奏填充。

每个 phrase 至少包含：
- `phrase_id`
- `source_start` / `source_end`
- `duration`
- `lyric_text`
- `word_timing` 或 `lyric_timing`
- `reference_audio_wav`
- `selection_reason`
- `qc_status`

自动边界建议：
1. 用 Whisper `word_timestamps` 获取候选歌词边界。
2. 用能量谷值 / vocal activity 排除上一句尾巴和下一句开头。
3. 用歌词提示复核目标句，但不能只信带提示 Whisper。
4. 导出 clean PCM WAV，要求 Whisper 能稳定转写为目标歌词。
5. 对 Seedance 最小 5s 的情况，优先让乐句从 `0.00s` 开始，尾部留情绪/尾音；不要在片头制造“准备开口”空间。

输出：
- `lip_sync_phrase_map.json`
- 每个候选 `*_reference.wav`
- 可选 `*_boundary_qc.json`

本地门禁：

```bash
python ~/.hermes/skills/creative/musical-mv-storyboard/scripts/validate_lip_sync_phrase_map.py \
  lip_sync_phrase_map.json \
  --shot-plan shot_plan.director.json

python ~/.hermes/skills/creative/musical-mv-storyboard/scripts/lip_sync_gate.py \
  --mode preflight \
  --phrase-map lip_sync_phrase_map.json \
  --shot-plan shot_plan.director.json \
  --output lip_sync_gate.preflight.json
```

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
- 对口型 shot 必须引用 `lip_sync_phrase_map.json` 里的 `phrase_id`，不能直接使用 section 或固定 shot 的 start/end 当作参考音频边界
- 不要把整段 chorus/final chorus 直接做成长口型镜头
- 生成服务最低 5s 时，成片仍可只取最有效 3-4s
- `build_video_prompts.py` 对 `lip_sync_closeup` 默认只给 Seedance 5s，再由 EDL 裁出目标 3-4s
- B-Roll/群舞负责填缝和承接，不要抢主唱爆点

### Step 3.2: Director Score（必须）

在 `shot_plan.auto.json` 之后、任何关键帧生图之前，必须由 LLM/导演写 `director_score.json`。

目标：先确定整支 MV 的上层导演逻辑，而不是逐个 shot 写漂亮画面。`director_score.json` 至少包含：
- `music_structure`：intro / verse / chorus / bridge / climax / outro 的时间段和音乐作用
- `emotional_curve`：全片能量曲线，标出压低、蓄力、爆发、余震、收束
- `visual_chapters`：每章的世界状态变化、色彩、空间、主体、音乐职责
- `shot_roles`：每个 shot 为什么存在、承接前一镜什么、把观众推向下一镜什么
- `contrast_map`：相邻 shot 的远近、动静、冷暖、人物/物体、单人/群体、现实/超现实反差
- `generation_strategy`：每个 shot 使用单图、3x3 动作板、口型特写、群舞板、B-roll 或后期特效

如果某个 shot 只写了“好看/大场面/更炸”，但没有 `shot_role`、`contrast_from_previous`、`handoff_to_next`，不得进入生图。

参考 `references/director-score.md`。

### Step 3.3: Visual Duration Plan（必须）

在写任何 Seedance prompt 前，必须先判断每个音乐单元到底需要多长画面、几个生成任务。

输出 `visual_duration_plan.json`，至少包含：
- `recommended_final_window`：这一组视觉高潮/铺垫最终覆盖的音乐窗口
- `story_beats`：观众必须看懂的动作变化
- `minimum_readable_seconds`：每个 beat 的最低可读时长
- `generation_units`：实际提交给 Seedance 的生成单位
- 每个 `generation_unit` 的 `music_start`、`music_end`、`final_duration`、`seedance_duration`、`max_major_actions`、`primary_visual_action`
- 每个 `generation_unit` 必须有独立的 `cinematic_keyframe_strategy`：这张关键帧应该是什么单一画面、来自哪些资产参考、为什么能承载这个动作

本地门禁：

```bash
python ~/.hermes/skills/creative/musical-mv-storyboard/scripts/validate_visual_duration_plan.py \
  visual_duration_plan.json \
  --output visual_duration_plan.validation.json
```

硬规则：
- 一个 Seedance 任务最多承载 1-2 个主要动作。
- 悬疑段不能只按 API 最大 15s 判断；要按“停顿、反应、延迟揭示”计算容量。
- 如果出现“观众看到但角色没看到”，必须优先拆成独立 `generation_unit`。
- 通过时长规划后，才能写 `seedance_video_prompt`。

参考 `references/visual-duration-planning.md`。

### Step 3.5: Preview Page Gate

在生视频之前必须生成或维护 `preview.html`。页面至少包含：
- 顶部“当前推荐观看版本 / 当前检查顺序”，不要把资料一股脑平铺
- 问题段小样、当前抽帧、最终成片放第一屏
- 全曲人声地图、歌词时间轴、2s/4s 爆点窗口
- 分镜表、镜头类型、短对口型目标时长、音乐理由
- 导演总谱：音乐结构、情绪曲线、视觉章节、shot 职责、承接反差
- 物品/场景角色复杂的 MV 必须先做 `prop_cast.json` 和 `asset_review` 物品演员表图片，确认馆藏/道具统一后再生单 shot 图
- `asset_review` 必须单独成区：浅背景、缩略图、文字说明、点击放大；不得和正式 `cinematic_keyframe` 混在一起
- 关键帧图、已生成视频、QC 抽帧、最终预览
- EDL/剪辑时间线
- 人物/服装连续性表：`costume_state_id`、换装事件、哪些镜头必须同服装
- 图片、抽帧、视频默认缩略显示；点击图片放大、点击视频再播放；每个媒体必须有标题/说明，禁止全尺寸媒体平铺导致看板不可读
- 页面必须有可收起索引边栏，能快速跳到当前成片、音乐爆点、导演总谱、时间线、分镜详情和每个 shot
- 旧版本、技术分析、长 prompt 默认折叠

不要等用户提醒才更新。每次改文件后都要重建预览页。

推荐使用：

```bash
python ~/.hermes/skills/creative/musical-mv-storyboard/scripts/preview_builder.py \
  /path/to/project \
  --output /path/to/project/previews/preview.html
```

如自动发现不准，再显式调用底层构建器：

```bash
python ~/.hermes/skills/creative/musical-mv-storyboard/scripts/build_preview.py \
  shot_plan.director.json \
  --prompts video_prompts.json \
  --climax music_climax_analysis.json \
  --director-score director_score.json \
  --keyframe-dir assets/keyframes \
  --video-dir videos/seedance \
  --qc-video-dir videos/seedance/qc_audio \
  --final-video videos/final/final_output.mp4 \
  --focus-video videos/final/issue_excerpt.mp4 \
  --proof-dir videos/final/lipsync_proof \
  --contact-sheet videos/final/final_contact.jpg \
  --asset-review assets/asset_review/asset_cast.png \
  --asset-review-manifest asset_review_manifest.json \
  --edit-decision-qc edit_decision_qc.json \
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
| `costume_state_id` | 人物服装状态，必须引用 `wardrobe_plan.json` |
| `wardrobe_continuity_note` | 本镜头是否同服装、是否换装、换装是否有音乐/剧情交代 |
| `reference_style` | 视觉参考 |
| `lip_sync_notes` | 仅对口型：精确歌词、嘴部状态、时间窗口 |
| `lip_sync_phrase_id` | 仅对口型：绑定 `lip_sync_phrase_map.json` 中的完整乐句 |
| `reference_audio_wav` | 仅对口型：由完整乐句导出的 clean PCM WAV |
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
5. 服装/发型变化是否有明确设计，而不是模型漂移
6. 镜头长度是否足够短、足够准

### Step 4.5: Wardrobe / Look Continuity Gate

真人 MV 或任何连续人物叙事，在关键帧生图前必须创建 `wardrobe_plan.json`：

- `main_character`：脸、发型、基础服装、禁用造型
- `costume_states`：每种服装状态的 ID 和含义
- `shot_costume_map`：每个 shot 对应哪个 `costume_state_id`
- `change_events`：如果换装，必须写清发生在哪个音乐/剧情节点
- `qc_rules`：哪些镜头必须同服装，哪些只是灯光变化不是换装

规则：
- 同一时空连续叙事默认不换装。
- 允许 MV 换装，但必须发生在 verse/chorus/bridge/final hook 等音乐结构切换处。
- 如果没有 `change_event`，模型生成出不同衣服就是穿帮。
- 如果只是灯光、舞台化、外套开合、工牌摆动，必须写明“同一套基础服装的表演变化”，不能让模型理解成新衣服。
- 如果需要酷炫换装，必须把换装桥放在音乐结构切换或爆点前，例如 `bridge -> final hook`；换装前后要有明确 `costume_state_id`，并在画面/剪辑上让观众看到这是设计事件。
- `seedance_image_prompt` 和 `seedance_video_prompt` 必须包含该 shot 的 `costume_state_id` 和 `wardrobe_continuity_note`。

### Step 5: Asset Review + Keyframes + Video Generation

推荐顺序：
1. 生主角/角色参考图
2. 写 `wardrobe_plan.json`，锁定服装状态和换装事件
3. 对复杂人物/物品/车辆/场景，先生 `asset_review` 图和对应 manifest：浅背景、软光、单资产清楚展示，确认“它长什么样”
4. 通过 `asset_review` 后，再生每个 shot 的 `cinematic_keyframe`：正式光影、气氛、运动前一帧、构图
5. 对复杂段落，按 `visual_duration_plan.generation_units` 逐个生成 `cinematic_keyframe`；一个生成单位一张单一镜头图
6. 更新 `preview.html`，资产确认区必须在关键帧/视频区之前
7. 用户或 Agent QC 后，再串行提交 Seedance 视频

`asset_review` 规则：
- 背景用浅灰、米白、修复室、采集台或中性空间；目标是可读性，不是戏剧感。
- 人物/服装/车辆/道具要完整、清楚、正侧或三分之四角度；不要被暗光、烟雾、强反光遮住。
- 古董/馆藏要先真实：包浆、氧化、磨损、裂纹、旧修复痕迹和材料质感成立；不要做成崭新金光道具。
- MV 动势、夜景、舞台灯、红激光、金光、超自然效果只能进入 `cinematic_keyframe` 或视频 prompt。
- 如果 `asset_review` 都看不清或风格不对，禁止继续做正式 shot 图。
- 禁止把 `asset_review`、物品演员表、角色设定表、contact sheet、storyboard grid 直接作为 Seedance `image_urls`。如果上传图本身是拼贴/表格，即使 prompt 写“不要显示网格”，也必须停止，因为 Seedance 会优先动化输入图本身。

Seedance 规则：
- 真人、人脸、主唱、对口型、人物一致性重要的 shot：默认 `doubao-seedance-2.0-face`
- 非真人、纯物体、风景、展品、抽象 B-roll：默认 `doubao-seedance-2.0`
- `doubao-seedance-2.0-fast-face` / `doubao-seedance-2.0-fast` 只用于低成本方向草测；用户明确进入候选片段或最终片段时禁止默认使用 fast
- MV 预览优先 `480p` 控成本；需要最终清晰度再考虑更高方案
- 默认 `generate_audio=false`；需要诊断模型是否理解参考音频/歌词时，可对单个口型 shot 临时使用 `generate_audio=true`，但生成音频只能用于 QC，不能进最终混音
- `image_urls` 传参考图 URL，不要默认 base64 给 Seedance
- `image_urls` 的主图必须是单一正式镜头关键帧：人物、空间、构图、光线已经接近最终画面；资产图只能作为生成关键帧的上游参考，不能作为 I2V 主图
- 每个视频 prompt 必须写清楚“不要自带音乐/BGM，最终会后期叠加完整歌曲”
- 对口型镜头的 `seedance_video_prompt` 必须来自 `lip_sync_phrase_map`：包含完整乐句、参考音频角色、歌词时间轴和嘴型任务；不能只写 “she sings”

口型 shot lab 规则：
- 先只生成单个口型 shot，不要立刻合成全片。
- 必须产出两种 QC 文件：`seedance_raw_with_generated_audio.mp4` 和 `same_video_with_reference_audio.mp4`。
- 判断标准以“同画面贴回主歌/参考音频是否可用”为准；Seedance 自带声音只用于诊断是否改词、重唱或节奏重构。
- 如果 Seedance 自带声音改词但贴回主歌视觉可接受，可以记录为“视觉可用、生成音频不可用”。

### Step 6: Post-Production

合成规则：
- 所有片段统一规格、无音频轨
- lip-sync 附近硬切，不用 xfade/crossfade
- 最终单独混入 `song.mp3`
- 生成 `*_edl.json` 记录 source、timeline_start、timeline_end、duration、用途
- 生成 `*_contact.jpg` 抽帧总览
- 验证最终视频/音频时长

### Step 6.2: Edit Decision QC（必须）

只要同一 shot 存在多个裁剪、多个重生版本、或“干净但弱 / 有小 bug 但更有音乐势能”的取舍，必须先做 `edit_decision_qc.json`，再推荐进 `preview.html` 或 EDL。

模板：`templates/edit_decision_qc.example.json`。

运行：

```bash
python ~/.hermes/skills/creative/musical-mv-storyboard/scripts/score_edit_candidates.py \
  edit_decision_qc.json \
  --write
```

评分维度：
- `music_alignment`：是否保住音乐短语、蓄力、鼓点或 drop
- `story_completeness`：是否保住镜头叙事任务
- `handoff_energy`：是否能把观众推向下一个 shot
- `visual_continuity`：人物、服装、空间、运动方向是否连续
- `bug_maskability`：缺陷是否轻微、能否用闪白/硬切/裁切/字幕遮住，分越高越容易遮
- `editability`：是否给后期留下可用 handles

规则：
- `blocking_issues` 包含身份崩坏、宫格泄漏、严重口型错位、不可读画面时，该候选不能成为主推荐。
- `preview.html` 第一屏必须展示 `recommended_candidate`，备选版本默认折叠。
- 如果最终选择不是脚本推荐，必须在 scorecard 写明人工 override 原因。

### Step 6.3: Final Edit Gate（最终合成前硬门禁）

`edit_decision_qc.json` 只负责判断候选；最终 EDL 还必须证明自己引用了推荐候选。最终合成前必须运行：

```bash
python ~/.hermes/skills/creative/musical-mv-storyboard/scripts/prepare_final_edit.py \
  --discover-root . \
  --edl videos/final/final_edl.json \
  --output videos/final/final_edit_gate_report.json \
  --require-edl
```

如果还没生成 EDL，只想先看当前推荐候选：

```bash
python ~/.hermes/skills/creative/musical-mv-storyboard/scripts/prepare_final_edit.py \
  --discover-root . \
  --output final_edit_gate_report.json
```

门禁规则：
- 缺 `recommended_candidate`：失败
- 推荐候选有 `blocking_issues`：失败
- EDL 没有对应 shot：失败
- EDL 引用了非推荐候选：失败
- EDL 既没有 `edit_decision_candidate_id`，也无法从 `source` 证明使用推荐视频：失败

音频时间轴规则：
- `song.mp3` 是 immutable master timeline。正片、封面、字幕、HyperFrames/React overlay 都必须对齐它。
- A/B/C 对口型小样确认后，把结果写入 EDL，例如 `confirmed_variant: "C"`、`lip_sync_offset_seconds: 0.50`。
- 后期改封面、字幕、调色、特效时，不能改变 `timeline_start`、`timeline_end` 和 `lip_sync_offset_seconds`。
- 封面/标题卡默认用 `replace first N seconds`：封面占用 0-N 秒，后面接原片 N 秒后的内容，总时长不增加。
- 只有明确需要片头新增时才用 `insert N seconds`；一旦 insert，必须整体重算 EDL、字幕、口型 proof 时间点。
- 每次最终导出后，从最终成片导出所有口型 proof clips，并放进 `preview.html` 第一屏或“口型复查”区域。

推荐本地门禁：

```bash
python ~/.hermes/skills/creative/musical-mv-storyboard/scripts/export_lipsync_proofs.py \
  final_edl.json \
  --final-video final_output.mp4 \
  --output-dir lipsync_proof \
  --update-edl

python ~/.hermes/skills/creative/musical-mv-storyboard/scripts/validate_audio_lock.py \
  final_edl.json \
  --final-video final_output.mp4 \
  --require-proofs

python ~/.hermes/skills/creative/musical-mv-storyboard/scripts/lip_sync_gate.py \
  --mode final \
  --phrase-map lip_sync_phrase_map.json \
  --shot-plan shot_plan.director.json \
  --edl final_edl.json \
  --final-video final_output.mp4 \
  --require-proofs \
  --output lip_sync_gate.final.json
```

ffmpeg 原则：

```bash
ffmpeg -y -i final_silent.mp4 -i song.mp3 \
  -map 0:v -map 1:a \
  -c:v copy -c:a aac -b:a 192k \
  -shortest final_complete.mp4
```

### Step 6.4: Rhythm Audit Gate

任何最终剪辑、删段、插段、顺延或重排后，必须先跑节奏审计再交付：

```bash
python ~/.hermes/skills/creative/musical-mv-storyboard/scripts/rhythm_audit.py \
  --edl final_edl.json \
  --audio-analysis audio_analysis.json \
  --climax music_climax_analysis.json \
  --shot-plan shot_plan.director.json \
  --output-json rhythm_audit.json \
  --output-md rhythm_audit.md
```

如果 `rhythm_audit.md` 显示高潮落在安静/归位/空镜职责上，或者关键剪点远离 beat，需要先修 EDL，不要先重生图或重跑视频。

## Required Outputs

| 文件 | 说明 |
|------|------|
| `song.mp3` | 主歌曲 |
| `voice_director_plan.json` | 声音导演稿：情绪、停顿、重音、A/B/C 试音策略 |
| `audio_analysis.json` | Whisper + beat/energy 分析 |
| `music_climax_analysis.json` | 2s/4s 音乐爆点窗口 |
| `music_timeline.json` | 段落化时间线 |
| `lip_sync_phrase_map.json` | 对口型完整人声乐句地图，所有口型 shot 的 source of truth |
| `director_score.json` | 导演总谱：音乐结构、情绪曲线、视觉章节、shot 职责、承接反差 |
| `visual_duration_plan.json` | 视觉时长规划：音乐窗口、戏剧 beat、最低可读时长、Seedance 生成单位拆分 |
| `prop_cast.json` | 物品/馆藏演员表：物品类别、作用、出场 shot、统一风格 |
| `assets/asset_review/*` | 人物/物品/服装/车辆/道具资产确认图：浅背景、清楚、可判断长相 |
| `shot_plan.auto.json` | 脚本初稿 |
| `shot_plan.director.json` | LLM/导演修正后的最终分镜 |
| `video_prompts.json` | 生图/生视频 prompts |
| `preview.html` | 可视化项目预览 |
| `edit_decision_qc.json` | 多候选剪辑评分门禁，决定哪个裁剪/版本进入 preview 和 EDL |
| `final_edit_gate_report.json` | 最终 EDL 硬门禁报告，证明 EDL 使用推荐候选 |
| `lip_sync_gate.preflight.json` / `lip_sync_gate.final.json` | 对口型规划和最终 proof 硬门禁报告 |
| `rhythm_audit.json` / `rhythm_audit.md` | 最终剪辑节奏审计：音乐、歌词、beat、爆点和镜头职责对齐 |
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
- `references/voice-direction.md`：声音导演、A/B/C 试音、声音模板冻结
- `references/audio-lock-policy.md`：主音频时间轴、封面 replace/insert、EDL 门禁
- `references/post-production-sound.md`：配音/人声后期处理、BGM ducking、响度控制
- `references/director-score.md`：导演总谱、视觉章节、shot 职责和承接反差
- `references/visual-duration-planning.md`：根据音乐窗口和戏剧动作容量判断视频长度与生成单位
- `references/director-template.md`：结构化分镜模板
- `references/prompt-craft.md`：视频 prompt 写法
- `references/shot-types.md`：镜头类型定义
- `references/edit-decision-qc.md`：剪辑候选评分、主推荐选择和阻塞规则
- `references/workflow.md`：端到端 workflow 示例

## Scripts

| 脚本 | 功能 |
|------|------|
| `scripts/analyze_audio.py` | Whisper 转录 + librosa beat/energy 分析 |
| `scripts/analyze_climax_windows.py` | 轻量爆点窗口分析 |
| `scripts/build_music_timeline.py` | 从 audio_analysis.json 构建时间线 |
| `scripts/classify_musical_shots.py` | 基于音频数据的初步镜头分类 |
| `scripts/validate_visual_duration_plan.py` | 校验视觉时长规划和 Seedance 生成单位拆分 |
| `scripts/build_video_prompts.py` | 从 shot plan 生成 creative prompts |
| `scripts/build_preview.py` | 生成 preview.html |
| `scripts/preview_builder.py` | 自动发现项目资产并重建 preview.html，避免每次手工补参数 |
| `scripts/generate_elevenlabs_song.py` | ElevenLabs 音乐生成 |
| `scripts/export_lipsync_proofs.py` | 从最终成片导出口型 proof clips |
| `scripts/validate_audio_lock.py` | 校验 EDL、封面模式、口型 offset 和最终时长 |
| `scripts/lip_sync_gate.py` | 对口型 preflight/final 硬门禁，检查乐句、clean WAV、offset 和 proof |
| `scripts/rhythm_audit.py` | 剪辑节奏审计，检查 EDL 是否踩歌词、beat、爆点和 shot 职责 |
| `scripts/score_edit_candidates.py` | 多候选剪辑加权评分，生成 `recommended_candidate` 和 `ranking` |
| `scripts/prepare_final_edit.py` | 最终合成前硬门禁，校验 EDL 是否引用剪辑评分推荐候选 |

## Blood Lessons

- 不做 `music_climax_analysis.json` 就会把爆点放错，画面再大也不成立。
- 不做 `director_score.json` 就会陷入单 shot 修补：每个镜头单看还行，连起来没有情绪曲线、反差和递进。
- 不做 `visual_duration_plan.json` 就会把导演剧情硬塞进一个 Seedance 任务。15s 是 API 上限，不是 15s 戏剧容量；悬疑和爆点必须先拆 beat 再拆生成单位。
- 对口型不是越长越好。短、准、踩点，比 7-8s 长口型更可信。
- 好的完整对口型镜头可以保留，但必须来自实际成片验证。
- 对口型的根因经常不是 prompt，而是音频切片边界错。先用完整人声乐句和 clean WAV 锁 `phrase_id`，再让视频服务这个乐句。
- 大场面必须匹配音乐。`shot_11_v2` 这类“画面更大但不踩音乐爆点”的镜头不能替代真正爆点。
- 在强人声爆点前可以加 3s 左右的半对口型桥段，把观众带入主对口型镜头。
- 用户说“爆点不对”时，先查音乐窗口和 EDL，不要先重生图/视频。
- 用户说“节奏不对”时，先跑 `rhythm_audit.py` 看当前画面源时间是否贴住歌词/beat/爆点，不要凭肉眼直接裁。
- 合成问题优先修 EDL/ffmpeg，不要重新烧 Seedance。
- 封面、标题、字幕、特效是后期层，不得破坏已锁定的歌曲时间轴。封面默认替换前 N 秒，不插入到正片前。
- A/B/C 已确认的口型窗口必须从最终成片导出 proof clips 复查；如果 proof 坏了，先查时间轴是否被后期移动。
- 版本命名要清楚：`v1`、`v2_replace02_11`、`v3_lipsync_climax` 这类命名能避免误用旧片段。
- 资产确认图不是正式镜头图。用黑背景、暗光和舞台气氛去确认古董/服装/车辆，只会让人看不清并误判风格；先用浅背景确认真实形态，再进入正式 MV 光影。
- 剪辑判断不能只看“有没有某个 bug”。例如为了避开最后 0.5 秒正脸而切掉音乐和叙事势能，会让桥段变弱；轻微可遮掩 bug 通常低于音乐完整性和接镜头能量。
- `edit_decision_qc.json` 只能说明“应该选谁”，不能保证最终 EDL 真的用了它；最终合成前必须跑 `prepare_final_edit.py`，让错文件进不了成片。
- 自动化不是完全不判断，而是把判断点变成可执行门禁：`lip_sync_gate.py`、`rhythm_audit.py`、`preview_builder.py` 必须比临时口头判断优先。
