# Musical MV Storyboard · Codex 法则

## 根本目标

本项目的目标不是临时做完一个 MV，而是持续打磨 `musical-mv-storyboard` skill，直到它能稳定自动化生产。

Codex 在本目录工作时必须始终围绕三件事：

- 创造和完善 `SKILL.md`
- 严格利用和遵循 `SKILL.md`
- 从每次失败和成功中反向迭代 `SKILL.md`

## 必须先读 Skill

每次处理 MV 规划、生图、生视频、剪辑、口型、音乐分析、preview 页面之前，必须先查看当前目录的 `SKILL.md`，并按其中流程执行。

禁止只凭当前对话记忆、临时经验或局部问题直接写 prompt、调用接口、剪视频。

## Director Score 优先

任何单个 shot 的执行，都必须服从上层导演逻辑：

- `director_score`
- `shot_plan`
- `visual_duration_plan`
- `wardrobe_plan`
- `lip_sync_phrase_map`（如果涉及口型）

如果局部修复方案和上层导演意图冲突，必须先停下来修正计划，不能直接继续生成。

## 视频 Prompt 门禁

任何 Seedance/APImart 视频 prompt 提交前，必须确认 prompt 显式继承：

- 这个 shot 在全片中的职责
- 对应音乐时间和音乐理由
- 承接上一镜、交给下一镜的关系
- 当前服装/换装状态
- 是否跳舞、对口型、群舞、B-roll 或转场

缺少这些字段时，不允许调用付费视频接口。

## 失败必须沉淀

如果出现跑偏、穿帮、口型错位、音乐不匹配、prompt 违背导演总谱等问题，不能只修当前文件。

必须判断是否需要更新：

- `SKILL.md`
- `references/`
- `scripts/`
- preview 门禁逻辑

目标是让下一次 Codex 不再犯同类错误。

## Preview 必须维护

任何关键帧、视频、EDL、最终预览或重要判断变更后，必须同步维护项目 `preview.html`。

preview 的第一屏必须让人快速看到：

- 当前推荐版本
- 当前问题片段
- 当前判断
- 下一步该看什么

旧版本默认折叠，不能干扰判断。
