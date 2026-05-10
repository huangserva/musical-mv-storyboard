# 实战案例：Hollow Hearts Echo 60s MV

## 项目概况
- 歌曲：Hollow Hearts Echo（抒情电子，123 BPM）
- MV 时长：60s（原曲 135s-195s 段）
- 风格：电影感暗黑 MV，冷蓝灰→暖金渐变
- 4 张 Seedance I2V 关键帧，零文字污染

> 这是早期实战案例，主要保留成本纪律、Whisper、硬切、EDL 经验。新项目必须额外先跑 `music_climax_analysis.json`，并把对口型成片窗口压到 3-4s；生成 5s 不代表成片必须用满 5s。

## 60s 片段拆分方案（最终版）

```
时间轴:  0s                                                    60s
         |0---11|11-14|14---22|22-25|25---36|36-41|41--50|50-60|
         |  B   |🔴S  |  B   |🔴S  |  B   |🔴S  |  B  |  B  |
原曲:    135   146   151.88 156   159.78 163.86 167.88  184  195
```

### 8 个片段明细

| # | 类型 | MV时间 | Seedance时长 | 原曲歌词 | 关键帧 | Prompt 方向 |
|---|------|--------|-------------|---------|--------|------------|
| A | 🎬 B-roll | 0-11s | 10s | （器乐桥段） | shot_01 | 桥上剪影，雾雨弥漫 |
| B | 🔴 口型 | 11-14s | 5s | "Oh the ghost of yesterday still calls my name" | shot_02 | 温室近景，她唱歌，嘴唇张开 |
| C | 🎬 B-roll | 14-22s | 10s | "A whispered echo fueling this flame" | shot_02 | 温室中景，雨打玻璃，蕨类摇曳 |
| D | 🔴 口型 | 22-25s | 5s | "Lost in shadows a fading light" | shot_03 | 街道中景，她行走并唱歌 |
| E | 🎬 B-roll | 25-36s | 10s | "break this endless night" + "This endless night" | shot_03 | 城市从暗变亮，灯一盏盏亮起 |
| F | 🔴 口型 | 36-41s | 5s | "It holds me tight" × 2（最高潮） | shot_03 | 她伸手，金色粒子从掌心爆发 |
| G | 🎬 B-roll | 41-50s | 10s | "It holds me tight"（拖长余韵） | shot_04 | 金色光粒飘散，城市暖光笼罩 |
| H | 🎬 B-roll | 50-60s | 10s | "And with the miracle she stayed" | shot_04 | 走向门，推门，金光淹没→淡出 |

### 选这 3 个口型点的理由

1. **B（11-14s）"ghost of yesterday"** — 副歌第一句，人声刚进入的锚点
2. **D（22-25s）"Lost in shadows a fading light"** — 歌词最具诗意视觉意象
3. **F（36-41s）"It holds me tight" × 2** — 整首歌能量最高点，重复两次爆发

### 关键帧复用策略

- shot_01 → 只有 A（纯剪影场景）
- shot_02 → B + C（口型短片和氛围片共用温室场景）
- shot_03 → D + E + F（街道场景承担最多片段）
- shot_04 → G + H（门的场景承担结尾）

## ⚠️ 踩坑教训（2026-05-07 实战）

### 1. 跳过 Whisper 转录 = 对口型完全失败
一开始没有跑 `analyze_audio.py` 做 Whisper 转录，直接生成了 lip-sync 视频。结果：
- prompt 里只写了 "she sings passionately" 这种泛泛描述
- 生成的嘴型完全随机，放在任何时间点都对不上音乐
- **必须先跑 Whisper 得到 word-level timestamps，再把精确歌词写进 Seedance prompt**

### 2. music_timeline.json 里 lyrics 没有时间戳
原 JSON 里 `sections[].lyrics` 只是纯字符串列表，没有 start/end 时间。
**必须用 `analyze_audio.py` 生成 `audio_analysis_60s.json`，然后合并到 `music_timeline.json`。**

### 3. 并行提交视频 = 烧钱
同时并行提交了多个 Seedance 任务（每个 $1.49），用户看到后台同时跑多个任务很不满。
**Seedance 任务一旦提交不可取消，必须串行：一个完成→用户确认→再提交下一个。**

### 4. ffmpeg 合成规则（实测踩坑）
- **绝对不能用 xfade 转场拼接 lip-sync 片段**：xfade 会改变视频总时长，把已经对准的 lip-sync 时间点搞偏
- **必须用 concat + 硬切**，前后不够用 `color=c=black` 黑屏填充
- 时间偏差（如差1秒）只需调整 atrim 的时间点，不需要重新生成视频
- 合成有问题不要重生成视频，修 ffmpeg 命令即可

### 5. 先验证再继续
生成第一个 lip-sync 片段后，**立即合成到音乐上发给用户确认**。确认口型"接近对上"后再生成下一个。如果先生成3个再发现方向不对，已经浪费 $4.47。

### 6. 视频生成前必须问用户
不要自己决定"重做一个更好的版本"。每次提交前都要确认。

## 技术要点

- **前置步骤**：先跑 `analyze_audio.py` 拿 Whisper word-level timestamps → 合并到 `music_timeline.json` → 再生成任何 lip-sync 视频
- Seedance I2V 时长：口型通常生成 5s 但成片只取最佳 3-4s；氛围镜头按 5/10/15s 规划
- 图片需要上传 imgur 获取公开 URL 后提交 APImart
- lip-sync prompt **必须包含精确歌词**（从 Whisper 转录结果提取）
- 最终 ffmpeg concat 按 timeline 排列 + 混入 60s 音乐
- Shot 04 结尾需要 ffmpeg 淡出效果（金光→白→黑）
