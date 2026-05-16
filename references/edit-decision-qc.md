# Edit Decision QC

剪辑判断不能靠“哪个 bug 更少”单点决策。MV 的剪辑候选必须按音乐、叙事和接镜头势能一起评分。

## When Required

只要出现以下任一情况，就必须创建 `edit_decision_qc.json`：

- 同一个 shot 有两个以上裁剪版本。
- 同一个 shot 有两个以上 Seedance 版本可选。
- 一个版本画面更干净，另一个版本音乐/叙事更完整。
- 用户或 Agent 对“该不该切掉某段”产生争议。

## Required Inputs

每个候选必须记录：

- `video`：候选视频路径。
- `contact_sheet`：抽帧图路径，便于快速扫问题。
- `source_in` / `source_out`：源视频使用范围。
- `timeline_in` / `timeline_out`：放入主歌时间轴的位置。
- `scores`：六项 0-10 分。
- `blocking_issues`：不可推荐的硬伤，例如身份崩坏、宫格泄漏、严重口型错位、不可读画面。
- `reasoning`：为什么给这个分。

## Rubric

默认权重：

| Criterion | Weight | Meaning |
|-----------|--------|---------|
| `music_alignment` | 0.25 | 是否保住音乐短语、蓄力、鼓点或 drop。 |
| `story_completeness` | 0.20 | 是否保住镜头本来的叙事任务。 |
| `handoff_energy` | 0.20 | 是否能自然把观众推向下一个 shot。 |
| `visual_continuity` | 0.15 | 人物、服装、空间、运动方向是否连续。 |
| `bug_maskability` | 0.10 | 缺陷是否轻微、能否用闪白/硬切/裁切/字幕遮住；分越高越容易遮。 |
| `editability` | 0.10 | 是否给后期留下可用 handles。 |

运行：

```bash
python ~/.hermes/skills/creative/musical-mv-storyboard/scripts/score_edit_candidates.py \
  edit_decision_qc.json \
  --write
```

脚本会写入：

- `ranking`
- `recommended_candidate`
- `recommendation_status`

最终合成前还必须校验 EDL 是否真的使用推荐候选：

```bash
python ~/.hermes/skills/creative/musical-mv-storyboard/scripts/prepare_final_edit.py \
  --discover-root . \
  --edl videos/final/final_edl.json \
  --output videos/final/final_edit_gate_report.json \
  --require-edl
```

EDL 里的候选片段建议写：

```json
{
  "id": "shot_09",
  "source": "videos/seedance/shot09_v8/shot09_v8_handoff_trim_music_102p85_110p05.mp4",
  "edit_decision_candidate_id": "trim_7p20_primary_candidate",
  "timeline_start": 102.85,
  "timeline_end": 110.05
}
```

## Decision Rules

- 主推荐必须是最高分的非阻塞候选，不是最保守候选。
- 轻微、可遮掩的 bug 通常低于音乐完整性和接镜头能量。
- 如果候选存在 `blocking_issues`，即使总分高也不能推荐为主版本。
- 预览页必须把 `recommended_candidate` 放在第一屏；旧版本和备选版本默认折叠。
- 如果最终选择不是脚本推荐，必须在 scorecard 里写清人工 override 原因。
