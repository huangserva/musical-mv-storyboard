# Lip-Sync Policy

## Core Principle: Selective Lip-Sync Points（选择性口型点）

**MV 不是全程对口型视频。** 全程 15s/20s 连续对口型既难做又不自然。

正确做法：在整首音乐中找到 2-4 个**人声高潮点 / 音乐爆点**（每段 3-5s），只在这些点做口型短片；其余全部用氛围、群舞、B-Roll 填充。

**先找爆点，再找口型点。** 口型点不是只看人声密度，也要看能量和 onset 起跳。先用 `scripts/analyze_climax_windows.py` 生成 `music_climax_analysis.json`，再决定 lip-sync 落点。

观众听到歌词 + 看到嘴巴在动 + 时间点对上 = 视觉上就是对口型。大脑会自动补全。

## Two Types of Clips

| 类型 | 时长 | Seedance prompt | 放置位置 | 数量 |
|------|------|----------------|---------|------|
| 🎬 氛围长片 | 5-15s | 场景动效：雨、雾、光影、行走、群舞 | 填充时间线，情绪铺陈 | 4-8 个 |
| 🔴 口型短片 | 3-5s | **包含具体歌词** + 嘴部动作 | 精确放在对应歌词/音乐爆点 | 2-4 个 |

**60s MV 典型分布**：口型 ~10-16s（3-4个 × 3-4s）+ 氛围/群舞 ~44-50s。

> 实战结论：Seedance 可以生成 5s，但成片不一定用满 5s。只取最有效的 3-4s 是正常做法，剩余时长由 B-Roll/群舞补齐。

## How to Identify Lip-Sync Points（如何找口型点）

### Step 1: 分析音频和爆点

从 `music_timeline.json` 的 `whisper_segments` 提取每句歌词的精确时间。

同时从 `music_climax_analysis.json` 读取：
- `top_4s_windows`：主要 lip-sync 候选窗口
- `top_2s_windows`：硬切、闪白、推拉、hero pose 候选窗口

### Step 2: 标记人声高潮

在连续选段内，根据以下条件选 2-4 个口型点：

1. **音乐爆点 + 有人声** — 最高优先级，必须优先考虑短对口型
2. **副歌第一句 / title drop** — 情绪锚点
3. **起跳前承接句** — 可用 3s 半对口型把观众带进完整副歌口型
4. **诗意画面句** — 歌词有强烈视觉意象

**不要选**：过渡句、重复拖长句的中段、低能量段落、纯粹大远景但看不清嘴的画面。

> 关键经验：大场面不是 lip-sync 的替代品。最强爆点如果有人声，应该让主唱在近中景/特写里唱出来；群舞和远景放在前后承接。

### Step 3: 选择 60s 片段（⚠️ 关键决策，选错全盘皆输）

> ⚠️ **Pitfall — 必须先分析全歌人声分布再选段**
>
> **不能凭直觉选"最后副歌+尾奏"！** 实际案例：Hollow Hearts Echo 3分钟195秒，选了135-195s（最后60s），结果最后30秒全是"It holds me tight"循环+纯音乐间奏，人声稀疏到可怜。
>
> **正确做法**：先对全曲跑 `analyze_audio.py`，列出所有 vocal segments + 人声密度，然后选**人声最密集的连续60秒**。
>
> ```python
> # 快速评估各60s窗口的人声密度
> for start in range(0, total_duration - 60, 10):
>     vocal_in_window = sum(seg['end']-seg['start'] for seg in whisper_segments 
>                           if seg['start'] >= start and seg['end'] <= start+60 and seg['text'].strip())
>     print(f"{start}-{start+60}s: {vocal_in_window:.0f}s vocal")
> ```
>
> 选 vocal_in_window 最大的窗口。如果有多个接近的，结合歌词情感强度选择。

### Step 4: 切割时间线

```
示例：60s MV（原曲 135s-195s）

时间轴:  0s                                                    60s
         |0---11|11-14|14---22|22-25|25---36|36-41|41--50|50-60|
         |  B   |🔴S  |  B   |🔴S  |  B   |🔴S  |  B  |  B  |
         桥段   ghost  flame  shadows night  endless holds  miracle

B = 10s 氛围长片（B-roll）
S = 5s 口型短片（lip-sync short）
共 8 个片段，3 个口型点
```

### Step 4: 生成对应 prompt

- **氛围长片** prompt 写场景动效（雨丝飘落、雾气流动、灯一盏盏亮起）
- **口型短片** prompt **必须包含具体歌词**（见下方 ⚠️）
- **关键帧可以复用**：同一个场景的氛围片和口型片共用一张 keyframe

> ⚠️ **CRITICAL — 口型短片 prompt 必须包含具体歌词**
>
> Seedance I2V **不能自动对口型**。如果不把歌词写进 prompt，生成的嘴型完全随机，跟音乐毫无关系，放在任何时间点都对不上。
>
> **正确做法**：从 `music_timeline.json` 提取该时间段的 Whisper 转录歌词，直接写入 Seedance prompt。
>
> 例：口型点 MV 11-15s = 原曲 146-150s，歌词 "ghost of yesterday"
> ```
> prompt: "Medium close-up, young person singing the words 'ghost of yesterday',
> mouth open forming the 'gh' consonant, then closing on 'day',
> emotional intensity, rain in background..."
> ```
>
> 即使有了歌词，Seedance 生成的嘴型也只是**大致看起来在唱**，不是逐字精确同步。
> 如果需要真正精确的口型，必须走 Step 5 的 Wav2Lip 流程。

### Step 5: 验证口型效果（先合成再继续）

**生成第一个 lip-sync 片段后，必须立即合成到音乐上验证时间对齐。**

1. 用 ffmpeg concat 硬切（见下方 ⚠️）把 lip-sync_01 放到正确时间点 + 音乐
2. 发给用户确认口型是否"接近对上"
3. **只有用户确认 OK 后，才能生成 lipsync_02**
4. 如果时间偏差（如差1秒），微调 concat 的 atrim 时间点即可，不需要重新生成视频

> ⚠️ **为什么必须先验证**：Seedance 生成的嘴型是近似的，即使 prompt 写了歌词也不保证能对上。如果先生成3个再发现全对不上，已经浪费 $4.47。先验证1个，确认方向正确再继续。

### Step 5.5: 冻结已确认口型 offset（A/B/C 门禁）

当用户在 A/B/C 小样里确认某个口型版本后，必须立即把结果写入 EDL 或旁路 QC JSON：

```json
{
  "shot_id": "shot_04",
  "confirmed_variant": "C",
  "lyric_start": 32.42,
  "timeline_start": 31.92,
  "lip_sync_offset_seconds": 0.50,
  "proof_required": true
}
```

规则：
- `lyric_start` 来自主歌曲/Whisper，是母版时间。
- `timeline_start = lyric_start - lip_sync_offset_seconds`，不是凭感觉拖动。
- 一旦用户确认，后续封面、字幕、HyperFrames、调色、特效都不能改变这个关系。
- 如果最终视频里口型坏了，第一反应是查 EDL/封面/concat 是否移动时间轴，不是重新生成 Seedance。
- 最终交付前，必须从最终成片导出该窗口的 proof clip；不能用中间小样冒充最终证明。

### Step 6: Wav2Lip 精确口型（如需真正对口型）

Seedance 生成的口型短片嘴型是近似的，**不是真正的 lip-sync**。

**需要真正对口型时**：
1. 用 Seedance I2V 生成基础视频（prompt 含具体歌词）
2. 提取对应时间段的音频片段
3. 用 `mv-lip-sync-pipeline` skill 跑 Wav2Lip

**可以跳过 Wav2Lip 的情况**（仅限氛围MV）：
- 口型短片 3-5s，观众注意力在画面整体而非嘴部
- 快速剪辑，每个口型片段只出现一瞬间
- 用户明确说"氛围MV"不要精确对口型

## Why This Works（为什么这样做更好）

| | 全程口型（旧方案） | 选择性口型点（新方案） |
|---|---|---|
| 生成难度 | 15-20s 连续口型极难 | 3-5s 短片轻松 |
| Seedance 质量 | 强制控制嘴型，画面质量下降 | 专注短爆点，画面和口型都更稳 |
| 时间线对齐 | 精确到每个音节，几乎不可能 | 只对 2-4 个点，精确放置 |
| 视觉效果 | 全程脸部特写，单调 | 氛围片 + 口型片交替，节奏丰富 |
| 观众感知 | 嘴型稍有偏差就很违和 | 短暂切到脸部，观众来不及细看 |

## When To Require Exact Lip-Sync (Wav2Lip)

### Seedance I2V 的口型能力极限

Seedance I2V 即使 prompt 写了精确歌词 + 嘴部描述，生成的口型也只是**近似**的（"接近对上"），不是逐字精确同步。

**实测发现**：
- face 模型 + 单图 + 5s 时长，生成效果可能接近静态图（几乎无动态）
- 标准 model 动态更好，但可能触发 PrivacyInformation 拒绝含写实人像的图
- 把歌词写进 prompt 确实比不写好（用户反馈"接近对上了"），但效果依赖运气
- 时间偏移1秒只需调整 ffmpeg 拼接时间点，不需要重新生成
- 7-8s 长口型容易暴露不准；3-4s 短口型更容易达到"像在唱"的观感

**结论**：Seedance lip-sync 是"近似的视觉暗示"，不是真正的对口型。MV 中它起的是"让观众感觉在唱"的作用，靠的是剪辑时机的配合，而非精确的嘴部运动。

### 可视化时间轴预览（强烈推荐）

在编排阶段生成一个 HTML 时间轴预览页面，对沟通效率提升巨大。

**效果**：用户一眼就能看到 60s 的完整编排——哪些是 lip-sync（红色不可裁）、哪些是 B-Roll（蓝色可裁）、歌词对应关系、pending 状态。比文字表格清晰10倍。

**关键元素**：
1. 横向 Gantt-style 时间轴，0-60s 刻度
2. 上轨：视频片段（红=lipsync，蓝=broll，黑=gap）
3. 下轨：歌词（金色=vocal，灰色=instrumental）
4. 下方表格：每段的详细信息和裁剪情况

用户看到预览后能快速给出编排调整意见，避免生成完再返工。

**仅在以下情况使用 Wav2Lip：**
- 唱跳 MV，需要逐帧精确对口型
- 用户明确要求"精确 lip-sync"而非"氛围 MV"
- 口型片段 >5s，观众有时间注意嘴部细节

**以下情况不需要 Wav2Lip：**
- 氛围 MV / 音乐短片 / 情绪片
- 短片 3-5s 且快速切换
- 观众注意力在画面整体而非嘴部细节

## Data-Driven Classification

从 `audio_analysis.json` 的 sections 读取 `vocal_density` 和 `avg_energy`：

- **口型点候选**：`vocal_density > 0.70 AND avg_energy > 0.60`
- **跳过口型**：`vocal_density < 0.30 OR avg_energy < 0.25`

最终选哪 2-3 个点必须结合歌词内容和情感弧线判断，不能只看数据。

## Prompt Rule

- **口型短片**：**必须包含该时间段的精确歌词文本** + "lips parting, mouth forming words, she sings"
- **氛围长片**：不提嘴部动作，描述视觉动效和氛围

## ⚠️ ffmpeg 合成规则（MV 视频拼接）

- **必须用 concat + 硬切**（`[v1][a1][v2][a2]concat=n=2:v=1:a=1`）
- **绝对不能用 xfade 转场拼接 lip-sync 片段**：xfade 会改变视频总时长，把已经对准的 lip-sync 时间点搞偏
- **Lip-Sync 成片窗口不可随意破坏**：先确定目标歌词窗口，生成 5s 后可只取最有效 3-4s；不要为了用满素材而拖长口型。B-Roll 负责填缝
- 前后时长不够用 **color source 黑屏填充**（`color=c=black:s=854x480:d=X:r=30`），不要拉伸/压缩其他片段
- **封面/标题卡默认 replace，不默认 insert**：封面替换原片前 N 秒，总时长不变；不要把封面插到正片前导致全片口型整体错位。
- **如果必须 insert 片头**：必须整体重算 EDL、字幕、口型 proof 时间点，并在文件名写清楚 `cover_insert_*`。
- **黑屏放在开头做封面时也按 replace 处理**，不要插在视频中间（除非是 lipsync 待补位占位符）
- 时间偏差（如差1秒）只需调整 atrim 的时间点，不需要重新生成视频
- **最佳合成方式**：先将所有片段（包括黑屏）预处理为统一分辨率/帧率/无音频的 h264，再用 concat demuxer 拼接，最后 `-map 0:v -map 1:a` 叠加完整音乐。这样可以避免混合有音频/无音频片段时 concat 断音的问题
- **必须维护 EDL**：每次插入、替换、剪短 lip-sync 后，写出 `*_edl.json`，记录 source、timeline_start、timeline_end、duration、用途，避免后续误用旧版本
- **必须导出最终 proof clips**：对每个 `proof_required=true` 的口型窗口，从最终 mp4 截出独立小片段，放到 preview.html 供复查。

```bash
# 正确示例：黑屏(10s) + lip-sync(5s) + broll(15s) + 音乐(30s)
ffmpeg -y \
  -f lavfi -i "color=c=black:s=854x480:d=10:r=30" \   # 黑屏填充
  -i lipsync.mp4 -i broll.mp4 -i music.mp3 \
  -filter_complex "
    [0:v]scale=854:480,setsar=1,fps=30[black];
    [1:v]scale=854:480,setsar=1,fps=30[v1];
    [2:v]scale=854:480,setsar=1,fps=30[v2];
    [3:a]atrim=0:10,asetpts=PTS-STARTPTS[a1];
    [3:a]atrim=10:15,asetpts=PTS-STARTPTS[a2];
    [3:a]atrim=15:30,asetpts=PTS-STARTPTS[a3];
    [black][a1][v1][a2][v2][a3]concat=n=3:v=1:a=1[v][a]
  " -map "[v]" -map "[a]" -c:v libx264 -preset fast -crf 23 -c:a aac -b:a 192k output.mp4
```

## ⚠️ Cost Discipline（视频生成成本纪律）

- **Seedance I2V 每次提交 ~$1.49 且不可取消**，提交前必须确认没有其他任务在跑
- **绝对不能并行提交**多个视频生成任务
- **重新生成前必须问用户**，不能自己决定重做
- 下载失败只修下载，绝不重提交
- 一个任务确认完成/用户满意后，再提交下一个
- **合成问题（时间偏移、拼接方式错误）不要重新生成视频**，修 ffmpeg 命令即可
