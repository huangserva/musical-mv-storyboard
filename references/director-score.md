# Director Score

`director_score.json` 是 MV 的导演总谱。它必须先于关键帧和 Seedance prompt 生成，用来防止项目退化成“单 shot 炫技”。

## Core Principle

先设计整支 MV 的观看体验：

```text
音乐结构 -> 全片情绪曲线 -> 视觉章节 -> shot 职责 -> shot 间反差/承接 -> 单 shot 图和视频
```

每个 shot 必须回答三件事：

- 它从前一个 shot 接住了什么？
- 它本身推进了什么？
- 它把观众推向下一个什么？

## Minimal Schema

```json
{
  "project_title": "Museum After Hours",
  "director_thesis": "闭馆后的博物馆从秩序中失控，女馆员成为唤醒整座博物馆的主唱/舞者。",
  "music_structure": [
    {
      "section_id": "intro",
      "start": 0.0,
      "end": 14.0,
      "music_role": "冷启动，建立空间和秩序",
      "energy": 1
    }
  ],
  "emotional_curve": [
    {
      "time": 0.0,
      "energy": 1,
      "state": "冷、静、空"
    },
    {
      "time": 110.0,
      "energy": 9,
      "state": "全馆第一次真正爆开"
    }
  ],
  "visual_chapters": [
    {
      "chapter_id": "ch01_order",
      "name": "闭馆后的秩序",
      "time_range": "0.0-22.0",
      "music_role": "让观众进入世界",
      "world_state": "博物馆像一台停止运转的机器",
      "visual_language": "冷蓝、空镜、对称、慢推",
      "shot_ids": ["shot_01", "shot_02"]
    }
  ],
  "shot_roles": [
    {
      "shot_id": "shot_10",
      "chapter_id": "ch05_full_awakening",
      "role": "全馆第一次爆开，不是单人 pose",
      "incoming_handoff": "承接 shot_09 的换装桥和规则改变",
      "outgoing_handoff": "把观众推向后续群舞/全馆响应",
      "contrast_from_previous": "从走廊线性推进切到中庭大空间爆发",
      "contrast_to_next": "从女主控制场域切到文物/群体加入",
      "generation_strategy": "3x3 action board + 1-2s hit clips + post-production hard cuts"
    }
  ]
}
```

## Chapter Design

视觉章节不是剧情摘要，而是“世界状态变化”。例如博物馆 MV：

| 章节 | 世界状态 | 作用 |
|------|----------|------|
| 闭馆后的秩序 | 冷、静、空、规则明确 | 让观众进入世界 |
| 第一批异常 | 灯、书、影子、展柜开始不听话 | 制造期待 |
| 女主成为唤醒者 | 她听见节奏，但还没完全掌控 | 建立主角职责 |
| 换装桥 | 世界规则改变，身份转换 | 为高潮换装提供理由 |
| 全馆苏醒 | 文物、恐龙、木乃伊、金属加入节奏 | 主爆点 |
| 余震和归位 | 天亮前恢复秩序，留下证据 | 收束和记忆点 |

## Shot Contrast Map

相邻 shot 必须主动设计反差，至少选 1-2 个维度：

- 远景 -> 近景
- 静止 -> 爆动
- 冷蓝 -> 红金
- 空间 -> 身体
- 人物 -> 展品
- 单人 -> 群体
- 现实秩序 -> 超现实失控
- 慢推 -> 硬切/闪白/速度 ramp

如果相邻 shot 都是“女主站在中庭、金光、正面 hero pose”，即使单张图好看，MV 也会失去冲击力。

## Generation Strategy Gate

不同 shot 应选择不同生成策略：

| 场景 | 推荐策略 |
|------|----------|
| 建立空间/氛围 | 单张关键帧 + 慢推/平移 |
| 口型主唱 | 单人参考 + clean phrase WAV + 短口型 lab |
| 换装/动作过程 | 3x3 action board，必要时拆单格 |
| 群舞/爆点 | 多个 1-2s hit clips + 后期硬切 |
| 物体苏醒 | 展品特写短片段，不要全塞进一个长镜头 |
| 收束/余韵 | 单图或慢镜头，保留呼吸感 |

## Gate Checklist

进入生图前检查：

- 是否有完整 `director_score.json`
- 每个 shot 是否有 `chapter_id`
- 每个 shot 是否有 `role`
- 每个 shot 是否写明 `incoming_handoff` 和 `outgoing_handoff`
- 爆点 shot 是否有清晰反差，而不是只是“更大、更亮”
- 动作/舞蹈/换装是否使用 action board，而不是单张 hero 图
- 全片是否有能量起伏，而不是每段都想炸
