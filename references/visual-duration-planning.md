# Visual Duration Planning

MV 自动化不能先假设 `one shot = one Seedance task`。先判断音乐窗口和戏剧动作容量，再拆生成单位。

## Required Order

1. 读取 `audio_analysis.json` 和 `music_climax_analysis.json`。
2. 找到真实音乐单元：铺垫、起跳、主爆点、余波。
3. 写 `story_beats`：每个观众必须看懂的动作变化。
4. 给每个 beat 标最低可读时间。
5. 决定 `generation_units`：每个 Seedance 任务最多 1-2 个主要动作。
6. 通过 `validate_visual_duration_plan.py` 后，才能写 Seedance prompt。

## Duration Heuristics

| Beat Type | Minimum Readable Time |
|-----------|------------------------|
| suspense discovery / character notices something | 4-6s |
| character checks but sees nothing | 3-5s |
| audience-only object anomaly | 2-4s |
| reflection / shadow reveal | 3-5s |
| chain reaction lights / alarms | 2-4s |
| explosive hit / object impact | 0.8-2s |
| emotional reaction turn | 1.5-3s |
| wide confirmation / resolution | 3-5s |

## Hard Rules

- If a music window contains more than 2 dramatic beats, do not submit it as one Seedance task.
- If a beat depends on “the audience sees it but the character does not,” isolate it as its own clip.
- If the prompt contains invisible director logic such as “she hears,” “she suspects,” or “the audience knows,” translate it into visible action first.
- A 15s Seedance limit is not the same as a 15s story capacity. Suspense often needs multiple generated clips inside one 15s music window.
- The final music window can be shorter than the sum of generated clip durations; EDL selects the best subranges.
