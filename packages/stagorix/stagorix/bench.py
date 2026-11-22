"""Delivery time, measured: analysis, draft render and final render of one clip.

`stagorix bench <video>` cuts the first 60 s, runs `stagorix analyze` on it, writes a
representative edit plan (captions, a label, a zoom, a whip, a speaker effect, an outro)
and renders it as a draft and as a final 9:16. Times are wall clock on this machine, so the
promise to a user ("a video in N minutes") rests on a measurement, not on a guess.
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
import time
from pathlib import Path

from pydantic import BaseModel

from stagorix.analysis.media import MediaError, _ffmpeg
from stagorix.render.motion import EditPlan, PlannedEffect, Source


class BenchResult(BaseModel):
    clip_seconds: float
    machine: str
    analysis_seconds: float
    draft_seconds: float
    final_seconds: float
    final_lufs: float | None
    notes: list[str]

    @property
    def total_minutes(self) -> float:
        return round((self.analysis_seconds + self.draft_seconds + self.final_seconds) / 60, 1)


def machine() -> str:
    cpu = platform.processor() or platform.machine()
    if sys.platform.startswith("linux"):
        for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("model name"):
                cpu = line.split(":", 1)[1].strip()
                break
    return f"{platform.system()} · {cpu} · {os.cpu_count()} CPUs"


def bench_plan(duration: float) -> EditPlan:
    """A typical short: captions all the way, a hook label, a zoom, a whip, one speaker effect, an outro."""
    fx = lambda e, at, s, **p: PlannedEffect(effect=e, at=at, seconds=s, reason="bench", params=p)  # noqa: E731
    effects = [
        fx("label", 0.3, 2.0, text="Benchmark", position="upper"),
        fx("camera.zoom", min(8, duration * 0.2), 1.0, scale=1.12),
        fx("camera.whip", min(15, duration * 0.35), 0.35),
        fx("speaker.blur", min(25, duration * 0.5), 2.0),
        fx("outro.card", max(duration - 3, 0), 3.0, title="Thanks for watching"),
    ]
    return EditPlan(
        duration=duration, sources=[Source(video="clip.mp4", analysis="analysis")], effects=effects
    )


def run_bench(
    video: Path,
    work: Path,
    seconds: float = 60,
    analyze_args: list[str] | None = None,
    browser: str | None = None,
) -> BenchResult:
    from stagorix.analysis.video import probe
    from stagorix.render.edit import Aspect, render_edit
    from stagorix.render.renderer import Quality

    work.mkdir(parents=True, exist_ok=True)
    clip = work / "clip.mp4"
    cmd = [_ffmpeg(), "-v", "error", "-y", "-i", str(video), "-t", f"{seconds}", "-c", "copy", str(clip)]
    if subprocess.run(cmd, capture_output=True, text=True, check=False).returncode != 0:
        raise MediaError(f"could not cut {video}")
    info = probe(clip)
    duration = round(info.frames / info.fps, 3) if info.fps else seconds

    start = time.perf_counter()
    analyze = [sys.executable, "-m", "stagorix", "analyze", str(clip), "--out", str(work / "analysis")]
    subprocess.run([*analyze, *(analyze_args or [])], check=True)
    analysis = time.perf_counter() - start

    notes = []
    if not (work / "analysis" / "transcript.json").exists():
        notes.append("no transcript: captions and transcription time are missing")
    plan = work / "plan.json"
    plan.write_text(bench_plan(duration).model_dump_json(indent=2), encoding="utf-8")
    # Wall clock includes staging (voice cut, mattes, clean plate), which the user waits for too.
    start = time.perf_counter()
    render_edit(plan, work / "draft.mp4", Aspect.VERTICAL, Quality.DRAFT, browser)
    draft = time.perf_counter() - start
    start = time.perf_counter()
    final = render_edit(plan, work / "final.mp4", Aspect.VERTICAL, Quality.FINAL, browser)
    final_seconds = time.perf_counter() - start
    return BenchResult(
        clip_seconds=duration,
        machine=machine(),
        analysis_seconds=round(analysis, 1),
        draft_seconds=round(draft, 1),
        final_seconds=round(final_seconds, 1),
        final_lufs=final.lufs,
        notes=notes,
    )
