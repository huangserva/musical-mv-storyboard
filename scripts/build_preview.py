#!/usr/bin/env python3
"""Generate a readable director preview HTML for musical MV projects.

The preview is a review board, not a data dump:
- current final / issue excerpt / contact sheet first when available
- music and climax decisions next
- shot table before detailed prompt cards
- older or technical material stays behind collapsible sections

Input:  shot_plan.json + optional video_prompts.json / climax analysis / media paths
Output: preview.html
"""

from __future__ import annotations

import argparse
import html
import json
import os
import sys
from pathlib import Path
from typing import Any


SHOT_COLORS = {
    "lip_sync_closeup": "#ef4444",
    "performance_medium": "#f59e0b",
    "dance_or_group": "#8b5cf6",
    "mv_broll": "#3b82f6",
    "transition": "#6b7280",
}

SHOT_ICONS = {
    "lip_sync_closeup": "🎤",
    "performance_medium": "🎭",
    "dance_or_group": "💃",
    "mv_broll": "🎬",
    "transition": "➡️",
}

SHOT_LABELS = {
    "lip_sync_closeup": "短对口型特写",
    "performance_medium": "真人表演",
    "dance_or_group": "舞蹈/群舞",
    "mv_broll": "MV 氛围画面",
    "transition": "转场",
}


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def load_json(path: Path | None) -> dict:
    if not path or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def path_arg(value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value).expanduser().resolve()
    return path if path.exists() else None


def relative_url(path: Path, output_path: Path) -> str:
    return os.path.relpath(path, output_path.parent)


def seconds(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def shot_duration(shot: dict) -> float:
    if "duration" in shot:
        return seconds(shot.get("duration"))
    return max(0.0, seconds(shot.get("end")) - seconds(shot.get("start")))


def pct(start: float, end: float, total: float) -> tuple[float, float]:
    if total <= 0:
        return 0.0, 0.2
    left = start / total * 100
    width = max((end - start) / total * 100, 0.2)
    return left, width


def find_media(media_dir: Path | None, stem: str, suffixes: tuple[str, ...]) -> Path | None:
    if not media_dir:
        return None
    for suffix in suffixes:
        candidate = media_dir / f"{stem}{suffix}"
        if candidate.exists():
            return candidate
    return None


def video_figure(path: Path | None, output_path: Path, title: str, note: str = "", muted: bool = False) -> str:
    if not path:
        return ""
    muted_attr = " muted" if muted else ""
    note_html = f'<span class="caption-note">{esc(note)}</span>' if note else ""
    return f"""
      <figure class="media-card">
        <video src="{esc(relative_url(path, output_path))}" controls{muted_attr} playsinline preload="metadata"></video>
        <figcaption>
          <span class="caption-title">{esc(title)}</span>
          <span>{esc(path.name)}</span>
          {note_html}
        </figcaption>
      </figure>
    """


def image_figure(path: Path | None, output_path: Path, title: str, note: str = "") -> str:
    if not path:
        return ""
    note_html = f'<span class="caption-note">{esc(note)}</span>' if note else ""
    return f"""
      <figure class="media-card">
        <img src="{esc(relative_url(path, output_path))}" alt="{esc(title)}">
        <figcaption>
          <span class="caption-title">{esc(title)}</span>
          <span>{esc(path.name)}</span>
          {note_html}
        </figcaption>
      </figure>
    """


def build_proof_gallery(proof_dir: Path | None, output_path: Path) -> str:
    if not proof_dir or not proof_dir.exists():
        return ""
    videos = sorted(proof_dir.glob("*.mp4"))
    if not videos:
        return ""
    figures = "".join(
        video_figure(path, output_path, f"口型 proof {index}", "从最终成片直接截出，不用中间小样代替。")
        for index, path in enumerate(videos, 1)
    )
    return f"""
      <div class="proof-block">
        <h3>最终口型 proof</h3>
        <div class="proof-grid">{figures}</div>
      </div>
    """


def build_timeline(shots: list[dict], total: float) -> str:
    ticks = "".join(
        f'<span style="left:{i / total * 100:.3f}%">{i}s</span>'
        for i in range(0, int(total) + 1, 10)
    ) if total > 0 else ""
    clips = []
    for shot in shots:
        stype = shot.get("shot_type", "mv_broll")
        color = SHOT_COLORS.get(stype, "#666")
        icon = SHOT_ICONS.get(stype, "")
        start = seconds(shot.get("start"))
        end = seconds(shot.get("end"), start + shot_duration(shot))
        left, width = pct(start, end, total)
        label = SHOT_LABELS.get(stype, stype)
        title = f"{shot.get('shot_id', '')} {label} {start:.2f}-{end:.2f}s"
        clips.append(
            f'<div class="clip" style="left:{left:.3f}%;width:{width:.3f}%;background:{color};" '
            f'title="{esc(title)}">{esc(icon)} {esc(shot.get("shot_id", ""))}</div>'
        )
    return f"""
      <div class="timeline-wrap">
        <div class="ticks">{ticks}</div>
        <div class="clip-bar">{''.join(clips)}</div>
      </div>
    """


def build_climax_tables(climax_analysis: dict) -> str:
    if not climax_analysis:
        return '<p class="muted">未提供 music_climax_analysis.json。正式做 MV 前必须补齐爆点窗口。</p>'

    def rows(items: list[dict]) -> str:
        html_rows = []
        for item in items[:10]:
            html_rows.append(
                "<tr>"
                f"<td>{seconds(item.get('start')):.2f}-{seconds(item.get('end')):.2f}s</td>"
                f"<td>{seconds(item.get('score')):.3f}</td>"
                f"<td>{seconds(item.get('energy')):.3f}</td>"
                f"<td>{seconds(item.get('onset')):.3f}</td>"
                "</tr>"
            )
        return "\n".join(html_rows)

    return f"""
      <div class="climax-grid">
        <div>
          <h3>Top 4s：短对口型候选</h3>
          <div class="table-wrap"><table>
            <thead><tr><th>时间</th><th>score</th><th>energy</th><th>onset</th></tr></thead>
            <tbody>{rows(climax_analysis.get("top_4s_windows", []))}</tbody>
          </table></div>
        </div>
        <div>
          <h3>Top 2s：闪白 / 硬切 / 推拉候选</h3>
          <div class="table-wrap"><table>
            <thead><tr><th>时间</th><th>score</th><th>energy</th><th>onset</th></tr></thead>
            <tbody>{rows(climax_analysis.get("top_2s_windows", []))}</tbody>
          </table></div>
        </div>
      </div>
    """


def build_shot_rows(shots: list[dict]) -> str:
    rows = []
    for shot in shots:
        stype = shot.get("shot_type", "mv_broll")
        label = SHOT_LABELS.get(stype, stype)
        exact = "短对口型 / 不随意拉长" if shot.get("requires_exact_lip_sync") else "可裁剪填缝"
        target = shot.get("target_lip_sync_duration") or ""
        climax = shot.get("climax_window") or ""
        if isinstance(climax, dict):
            climax = f"{seconds(climax.get('start')):.2f}-{seconds(climax.get('end')):.2f}s score={seconds(climax.get('score')):.3f}"
        rows.append(
            "<tr>"
            f"<td>{esc(shot.get('shot_id'))}</td>"
            f"<td>{seconds(shot.get('start')):.2f}-{seconds(shot.get('end')):.2f}s</td>"
            f"<td>{shot_duration(shot):.2f}s</td>"
            f"<td><span class='pill' style='--pill:{SHOT_COLORS.get(stype, '#666')}'>{esc(label)}</span></td>"
            f"<td>{esc(target)}</td>"
            f"<td>{esc(climax)}</td>"
            f"<td>{esc(shot.get('music_reason') or shot.get('lyrics') or '')}</td>"
            f"<td>{esc(exact)}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def build_shot_cards(
    shots: list[dict],
    prompt_map: dict[str, dict],
    output_path: Path,
    keyframe_dir: Path | None,
    video_dir: Path | None,
    qc_video_dir: Path | None,
) -> str:
    cards = []
    for shot in shots:
        shot_id = str(shot.get("shot_id", ""))
        stype = shot.get("shot_type", "mv_broll")
        color = SHOT_COLORS.get(stype, "#666")
        label = SHOT_LABELS.get(stype, stype)
        prompt = prompt_map.get(shot_id, {})
        image_prompt = prompt.get("image_prompt", shot.get("seedance_image_prompt", ""))
        video_prompt = prompt.get("video_prompt", shot.get("seedance_video_prompt", ""))
        keyframe = find_media(keyframe_dir, shot_id, (".jpg", ".jpeg", ".png", ".webp"))
        raw_video = find_media(video_dir, shot_id, (".mp4", ".mov", ".m4v"))
        qc_video = find_media(qc_video_dir, f"{shot_id}_with_song_excerpt", (".mp4", ".mov", ".m4v"))
        media = "".join(
            [
                image_figure(keyframe, output_path, f"{shot_id} 关键帧"),
                video_figure(raw_video, output_path, f"{shot_id} 原始片段", "应无独立 BGM。", muted=True),
                video_figure(qc_video, output_path, f"{shot_id} 配乐小样", "只用于口型/节奏复查。"),
            ]
        )
        cards.append(
            f"""
            <details class="card shot-card" style="border-left-color:{color}">
              <summary>{esc(shot_id)} · {esc(label)} · {seconds(shot.get('start')):.2f}-{seconds(shot.get('end')):.2f}s</summary>
              <div class="media-grid">{media}</div>
              <p><b>导演意图：</b>{esc(shot.get('director_intent', ''))}</p>
              <p><b>音乐理由：</b>{esc(shot.get('music_reason', ''))}</p>
              <p><b>视觉描述：</b>{esc(shot.get('visual_description', ''))}</p>
              <p><b>运镜：</b>{esc(shot.get('camera', ''))}</p>
              <p><b>灯光：</b>{esc(shot.get('lighting', ''))}</p>
              <p><b>对口型：</b>{esc(shot.get('lip_sync_notes', 'N/A'))}</p>
              <details class="prompt-box">
                <summary>生图 / 生视频 prompt</summary>
                <p><b>生图：</b>{esc(image_prompt)}</p>
                <p><b>生视频：</b>{esc(video_prompt)}</p>
              </details>
            </details>
            """
        )
    return "\n".join(cards)


def build_html(
    shot_plan: dict,
    video_prompts: dict | None,
    style: str,
    climax_analysis: dict | None,
    output_path: Path,
    final_video: Path | None = None,
    focus_video: Path | None = None,
    contact_sheet: Path | None = None,
    reference_image: Path | None = None,
    keyframe_dir: Path | None = None,
    video_dir: Path | None = None,
    qc_video_dir: Path | None = None,
    proof_dir: Path | None = None,
    edl_path: Path | None = None,
) -> str:
    shots = shot_plan.get("shots", [])
    total = seconds(shot_plan.get("duration"))
    prompt_map = {}
    if video_prompts:
        prompt_map = {str(p.get("shot_id")): p for p in video_prompts.get("prompts", [])}

    lip_count = sum(1 for s in shots if s.get("requires_exact_lip_sync"))
    lip_target_total = sum(seconds(s.get("target_lip_sync_duration"), shot_duration(s)) for s in shots if s.get("requires_exact_lip_sync"))
    final_video_html = video_figure(final_video, output_path, "当前推荐成片", "先完整播放，看整体节奏是否成立。")
    focus_video_html = video_figure(focus_video, output_path, "重点问题段复查", "只看这一段，用于判断口型遮掩、节奏或字幕是否自然。")
    contact_html = image_figure(contact_sheet, output_path, "当前成片抽帧", "快速看字幕、爆点、色调和镜头节奏。")
    reference_html = image_figure(reference_image, output_path, "主角 / 风格参考图", "用于确认角色一致性和视觉方向。")
    proof_html = build_proof_gallery(proof_dir, output_path)
    edl_note = f'<a class="file-chip" href="{esc(relative_url(edl_path, output_path))}">EDL</a>' if edl_path else ""

    if not final_video_html:
        final_video_html = """
        <div class="empty-hero">
          <h3>还没有最终成片</h3>
          <p>当前页面用于生视频前的导演门禁：先确认音乐爆点、短对口型落点、关键帧和 Seedance prompt，再提交付费视频。</p>
        </div>
        """

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>音乐剧 MV 导演看版 — {esc(style or '未命名项目')}</title>
<style>
:root {{
  color-scheme: dark;
  --bg:#07090d;
  --panel:#101722;
  --panel2:#0c111a;
  --line:#253044;
  --line2:#1a2333;
  --text:#e9eef7;
  --muted:#9aa6ba;
  --gold:#f2c56b;
  --blue:#74a8ff;
}}
* {{ box-sizing:border-box; }}
html {{ scroll-behavior:smooth; }}
body {{
  margin:0;
  background:
    radial-gradient(circle at 18% -10%, rgba(206,149,59,.22), transparent 32rem),
    radial-gradient(circle at 86% 12%, rgba(75,111,170,.20), transparent 30rem),
    linear-gradient(180deg,#07090d 0%,#0b0f16 55%,#07090d 100%);
  color:var(--text);
  font-family:"PingFang SC","Avenir Next","Helvetica Neue",sans-serif;
}}
.page {{ max-width:1380px; margin:0 auto; padding:28px 26px 42px; }}
.topbar {{ display:flex; justify-content:space-between; gap:18px; align-items:flex-start; margin-bottom:18px; }}
.kicker {{ color:var(--gold); font-size:12px; letter-spacing:.18em; text-transform:uppercase; margin:0 0 8px; }}
h1 {{ margin:0; font-size:34px; line-height:1.12; }}
h2 {{ margin:0; font-size:22px; }}
h3 {{ margin:0 0 10px; font-size:15px; color:#f6f1de; }}
p {{ line-height:1.7; }}
.subtitle,.muted {{ color:var(--muted); }}
.subtitle {{ margin-top:8px; max-width:760px; }}
.nav {{ display:flex; flex-wrap:wrap; gap:8px; justify-content:flex-end; max-width:580px; }}
.nav a,.file-chip {{
  color:#f7d991;
  text-decoration:none;
  border:1px solid rgba(242,197,107,.35);
  background:rgba(61,45,21,.52);
  border-radius:999px;
  padding:8px 12px;
  font-size:12px;
  white-space:nowrap;
}}
.rule {{ border:1px solid rgba(239,111,98,.45); background:rgba(50,16,20,.72); color:#ffd6cb; padding:14px 16px; border-radius:14px; margin:18px 0; font-weight:650; line-height:1.65; }}
.card {{ background:rgba(16,23,34,.86); border:1px solid var(--line); border-radius:18px; padding:18px; margin-bottom:16px; box-shadow:0 18px 50px rgba(0,0,0,.22); }}
.section-head {{ display:flex; justify-content:space-between; gap:16px; align-items:flex-start; margin-bottom:16px; }}
.eyebrow {{ margin:0 0 6px; color:var(--gold); font-size:12px; letter-spacing:.14em; text-transform:uppercase; }}
.hero-card {{ border-color:rgba(242,197,107,.42); background:linear-gradient(145deg,rgba(19,26,39,.96),rgba(16,23,34,.82)); }}
.hero-grid {{ display:grid; grid-template-columns:minmax(420px,1.2fr) minmax(320px,.8fr); gap:18px; align-items:start; }}
.review-panel,.empty-hero {{ background:rgba(6,9,14,.55); border:1px solid var(--line2); border-radius:16px; padding:16px; }}
.review-panel ol {{ margin:0 0 16px 20px; padding:0; color:#d8e1ef; line-height:1.75; }}
.mini-stack {{ display:grid; gap:14px; }}
.stats {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; margin:16px 0; }}
.stat {{ background:var(--panel2); border:1px solid var(--line2); border-radius:14px; padding:14px; }}
.stat .value {{ color:var(--blue); font-size:25px; font-weight:800; }}
.stat .label {{ color:var(--muted); font-size:12px; margin-top:3px; }}
.legend {{ display:flex; flex-wrap:wrap; gap:10px; color:#c4ccda; font-size:13px; margin:16px 0; }}
.dot {{ display:inline-block; width:12px; height:12px; border-radius:3px; margin-right:5px; vertical-align:-1px; }}
.timeline-wrap {{ background:#0d131b; border:1px solid var(--line2); border-radius:14px; padding:18px 12px 14px; overflow:hidden; }}
.ticks {{ position:relative; height:18px; font-size:11px; color:#687385; }}
.ticks span {{ position:absolute; transform:translateX(-50%); }}
.clip-bar {{ position:relative; height:42px; background:#181f29; border-radius:8px; overflow:hidden; }}
.clip {{ position:absolute; top:0; bottom:0; overflow:hidden; white-space:nowrap; text-overflow:clip; font-size:11px; line-height:42px; padding-left:4px; color:white; border-right:1px solid rgba(0,0,0,.25); text-align:center; font-weight:700; }}
.table-wrap {{ overflow:auto; border-radius:14px; border:1px solid var(--line2); }}
table {{ width:100%; border-collapse:collapse; background:#0d131b; min-width:760px; }}
th,td {{ border-bottom:1px solid #1f2937; padding:10px 11px; text-align:left; font-size:13px; vertical-align:top; }}
th {{ background:#171e28; color:#c3ccda; font-weight:700; position:sticky; top:0; }}
tr:hover td {{ background:#101a27; }}
.pill {{ background:var(--pill); color:white; border-radius:999px; padding:3px 8px; font-size:12px; white-space:nowrap; }}
.climax-grid,.media-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:14px; }}
.proof-block {{ border:1px solid rgba(239,68,68,.35); background:rgba(63,13,22,.35); border-radius:16px; padding:14px; }}
.proof-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:12px; }}
figure {{ margin:0; }}
img,video {{ width:100%; max-width:100%; border-radius:14px; border:1px solid #2a3448; display:block; background:#05070a; }}
figcaption {{ color:var(--muted); font-size:12px; margin-top:8px; word-break:break-word; line-height:1.45; display:grid; gap:3px; }}
.caption-title {{ color:#f8e7b4; font-weight:800; font-size:13px; }}
.caption-note {{ color:#c3ccda; }}
.shot-card {{ border-left:4px solid #666; }}
details {{ margin-top:8px; }}
summary {{ cursor:pointer; color:#f7d991; font-weight:800; list-style:none; }}
summary::-webkit-details-marker {{ display:none; }}
.details-card > summary,.shot-card > summary {{ margin:-18px; padding:18px; border-radius:18px; }}
.details-card[open] > summary,.shot-card[open] > summary {{ margin-bottom:16px; border-bottom:1px solid var(--line2); border-radius:18px 18px 0 0; }}
.details-card > summary::before,.shot-card > summary::before {{ content:"+"; display:inline-grid; place-items:center; width:20px; height:20px; margin-right:8px; border:1px solid rgba(242,197,107,.45); border-radius:50%; }}
.details-card[open] > summary::before,.shot-card[open] > summary::before {{ content:"-"; }}
.prompt-box {{ background:rgba(0,0,0,.18); border:1px solid var(--line2); border-radius:12px; padding:12px; }}
b {{ color:#cbd5e1; }}
.note {{ color:var(--muted); font-size:12px; text-align:center; margin-top:22px; }}
@media (max-width:900px) {{
  .page {{ padding:18px 12px 30px; }}
  .topbar,.section-head,.hero-grid {{ display:block; }}
  .nav {{ justify-content:flex-start; margin-top:14px; }}
  h1 {{ font-size:27px; }}
  .review-panel {{ margin-top:14px; }}
}}
</style>
</head>
<body>
<main class="page">
<header class="topbar">
  <div>
    <p class="kicker">Musical MV Director Board</p>
    <h1>音乐剧 MV 导演看版</h1>
    <div class="subtitle">{esc(style or '未设置风格')} · 先看结论，再看时间线，最后看技术细节。</div>
  </div>
  <nav class="nav">
    <a href="#review">当前成片</a>
    <a href="#music">音乐爆点</a>
    <a href="#timeline">剪辑时间线</a>
    <a href="#shots">分镜详情</a>
    {edl_note}
  </nav>
</header>

<div class="rule">核心规则：先分析全曲人声和爆点，再决定短对口型；视频片段不要自带 BGM，最终只叠加主歌曲。</div>

<section class="card hero-card" id="review">
  <div class="section-head">
    <div>
      <p class="eyebrow">Review First</p>
      <h2>当前推荐检查顺序</h2>
    </div>
  </div>
  <div class="hero-grid">
    {final_video_html}
    <aside class="review-panel">
      <h3>先看这三件事</h3>
      <ol>
        <li>完整播放当前成片，看音乐节奏和画面爆点是否一致。</li>
        <li>单独复查最终口型 proof，不要用中间小样代替最终验证。</li>
        <li>看抽帧图，确认色调、角色、艺术字和大场面是否统一。</li>
      </ol>
      <div class="mini-stack">{focus_video_html}{proof_html}{contact_html}{reference_html}</div>
    </aside>
  </div>
</section>

<details class="card details-card" id="music" open>
  <summary>音乐爆点与项目统计</summary>
  <div class="stats">
    <div class="stat"><div class="value">{total:.1f}s</div><div class="label">歌曲 / 成片目标时长</div></div>
    <div class="stat"><div class="value">{len(shots)}</div><div class="label">镜头数量</div></div>
    <div class="stat"><div class="value">{lip_count}</div><div class="label">短对口型镜头</div></div>
    <div class="stat"><div class="value">{lip_target_total:.1f}s</div><div class="label">目标口型总时长</div></div>
    <div class="stat"><div class="value">{esc(shot_plan.get('tempo_bpm', 0))}</div><div class="label">BPM</div></div>
  </div>
  <div class="legend">
    {''.join(f'<span><i class="dot" style="background:{color}"></i>{esc(SHOT_LABELS.get(stype, stype))}</span>' for stype, color in SHOT_COLORS.items())}
  </div>
  {build_climax_tables(climax_analysis or {})}
</details>

<details class="card details-card" id="timeline" open>
  <summary>MV 剪辑时间线</summary>
  {build_timeline(shots, total)}
  <div class="table-wrap" style="margin-top:14px"><table>
    <thead><tr><th>镜头</th><th>时间</th><th>时长</th><th>类型</th><th>目标口型</th><th>爆点窗口</th><th>音乐理由 / 歌词</th><th>剪辑规则</th></tr></thead>
    <tbody>{build_shot_rows(shots)}</tbody>
  </table></div>
</details>

<details class="card details-card" id="shots">
  <summary>分镜详情与 Prompt</summary>
  {build_shot_cards(shots, prompt_map, output_path, keyframe_dir, video_dir, qc_video_dir)}
</details>

<div class="note">数据来源：shot_plan + video_prompts + music_climax_analysis。页面职责：导演确认和付费生成前门禁。</div>
</main>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate readable director preview HTML from shot plan")
    parser.add_argument("shot_plan", help="Path to shot_plan.json")
    parser.add_argument("--prompts", help="Path to video_prompts.json")
    parser.add_argument("--climax", help="Path to music_climax_analysis.json")
    parser.add_argument("--style", default="", help="Project style name")
    parser.add_argument("--output", default="preview.html", help="Output HTML path")
    parser.add_argument("--final-video", help="Current recommended final video")
    parser.add_argument("--focus-video", help="Issue/focus excerpt video")
    parser.add_argument("--contact-sheet", help="Current final contact sheet image")
    parser.add_argument("--reference-image", help="Lead/reference image")
    parser.add_argument("--keyframe-dir", help="Directory containing shot_XX keyframes")
    parser.add_argument("--video-dir", help="Directory containing raw shot_XX videos")
    parser.add_argument("--qc-video-dir", help="Directory containing shot_XX_with_song_excerpt videos")
    parser.add_argument("--proof-dir", help="Directory containing final lip-sync proof clips")
    parser.add_argument("--edl", help="EDL json path")
    args = parser.parse_args()

    shot_plan_path = Path(args.shot_plan).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    if not shot_plan_path.exists():
        print(f"Error: {shot_plan_path} not found", file=sys.stderr)
        sys.exit(1)

    shot_plan = load_json(shot_plan_path)
    video_prompts = load_json(path_arg(args.prompts))
    climax_analysis = load_json(path_arg(args.climax))

    html_doc = build_html(
        shot_plan=shot_plan,
        video_prompts=video_prompts,
        style=args.style,
        climax_analysis=climax_analysis,
        output_path=output_path,
        final_video=path_arg(args.final_video),
        focus_video=path_arg(args.focus_video),
        contact_sheet=path_arg(args.contact_sheet),
        reference_image=path_arg(args.reference_image),
        keyframe_dir=path_arg(args.keyframe_dir),
        video_dir=path_arg(args.video_dir),
        qc_video_dir=path_arg(args.qc_video_dir),
        proof_dir=path_arg(args.proof_dir),
        edl_path=path_arg(args.edl),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_doc, encoding="utf-8")

    print(f"Preview: {output_path}")
    print(f"  Shots: {len(shot_plan.get('shots', []))}")
    print("  Open in browser to review")


if __name__ == "__main__":
    main()
