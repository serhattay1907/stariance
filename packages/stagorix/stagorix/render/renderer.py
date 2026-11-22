"""A thin renderer interface, so the engine does not depend on one renderer.

Everything that turns a composition and its props into a video goes through `Renderer`.
`RemotionRenderer` is the only implementation today; a second one (for example
HyperFrames, reviewed in 12.0) implements the same two methods (principle 5).

Quality has two levels:
- draft: half resolution, 15 fps and a fast encoder, for previews and variants.
- final: full resolution and 30 fps, then the whole mix is normalised to −14 LUFS.
"""

from __future__ import annotations

import json
import re
import subprocess
import time
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, Field

FINAL_FPS = 30
DRAFT_FPS = 15
DRAFT_SCALE = 0.5
TARGET_LUFS = -14.0  # YouTube and Instagram play loudness-normalised at about −14 LUFS
TRUE_PEAK = -1.0


class Quality(StrEnum):
    DRAFT = "draft"
    FINAL = "final"


def fps_for(quality: Quality) -> int:
    return DRAFT_FPS if quality is Quality.DRAFT else FINAL_FPS


class RenderJob(BaseModel):
    composition: str
    out: Path
    props: dict[str, Any] = Field(default_factory=dict)
    quality: Quality = Quality.FINAL
    browser: str | None = Field(default=None, description="Chrome/Chromium to use instead of the bundled one")


class RenderResult(BaseModel):
    path: Path
    renderer: str
    quality: Quality
    seconds: float = Field(description="Wall-clock render time")
    lufs: float | None = Field(default=None, description="Loudness after the final mix pass")


class Renderer(Protocol):
    """Turns a composition into a video. Compositions read `fps` from their props."""

    name: str

    def render(self, job: RenderJob) -> RenderResult: ...

    def still(self, job: RenderJob, frame: int) -> Path: ...


class RemotionRenderer:
    name = "remotion"

    def _args(self, job: RenderJob) -> list[str]:
        args: list[str] = []
        if job.props:
            props_file = job.out.with_suffix(".props.json")
            props_file.write_text(json.dumps(job.props), encoding="utf-8")
            args.append(f"--props={props_file}")
        return args

    def render(self, job: RenderJob) -> RenderResult:
        from stagorix.verify import _remotion

        start = time.perf_counter()
        job.out.parent.mkdir(parents=True, exist_ok=True)
        args = ["render", "src/index.ts", job.composition, str(job.out), "--codec=h264", *self._args(job)]
        if job.quality is Quality.DRAFT:
            args += [f"--scale={DRAFT_SCALE}", "--x264-preset=veryfast", "--crf=26", "--jpeg-quality=70"]
        _remotion(args, job.browser)
        lufs = normalize_loudness(job.out) if job.quality is Quality.FINAL else None
        return RenderResult(
            path=job.out,
            renderer=self.name,
            quality=job.quality,
            seconds=round(time.perf_counter() - start, 1),
            lufs=lufs,
        )

    def still(self, job: RenderJob, frame: int) -> Path:
        from stagorix.verify import _remotion

        job.out.parent.mkdir(parents=True, exist_ok=True)
        args = ["still", "src/index.ts", job.composition, str(job.out), f"--frame={frame}", *self._args(job)]
        if job.quality is Quality.DRAFT:
            args.append(f"--scale={DRAFT_SCALE}")
        _remotion(args, job.browser)
        return job.out


def default_renderer() -> Renderer:
    return RemotionRenderer()


def _loudnorm_stats(path: Path) -> dict[str, str] | None:
    """First loudnorm pass; None when the file has no audio."""
    from stagorix.analysis.media import _ffmpeg

    filt = f"loudnorm=I={TARGET_LUFS}:TP={TRUE_PEAK}:LRA=11:print_format=json"
    result = subprocess.run(
        [_ffmpeg(), "-hide_banner", "-i", str(path), "-vn", "-af", filt, "-f", "null", "-"],
        capture_output=True,
        text=True,
        check=False,
    )
    match = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", result.stderr)
    if result.returncode != 0 or match is None:
        return None
    return json.loads(match.group(0))


def normalize_loudness(path: Path) -> float | None:
    """Normalise the whole mix (voice + sound effects) to −14 LUFS, true peak ≤ −1 dBTP.

    Two passes: measure, then a linear gain where possible, so the dynamics stay as mixed.
    The video stream is copied, not re-encoded. Returns the loudness after the pass.
    """
    from stagorix.analysis.media import MediaError, _ffmpeg
    from stagorix.analysis.voice import measure_lufs

    stats = _loudnorm_stats(path)
    if stats is None or stats["input_i"] in ("-inf", "inf"):
        return None
    filt = (
        f"loudnorm=I={TARGET_LUFS}:TP={TRUE_PEAK}:LRA=11:linear=true"
        f":measured_I={stats['input_i']}:measured_TP={stats['input_tp']}"
        f":measured_LRA={stats['input_lra']}:measured_thresh={stats['input_thresh']}"
        f":offset={stats['target_offset']}"
    )
    tmp = path.with_name(path.stem + ".mix" + path.suffix)
    cmd = [_ffmpeg(), "-v", "error", "-y", "-i", str(path), "-c:v", "copy", "-af", filt]
    cmd += ["-ar", "48000", "-c:a", "aac", "-b:a", "192k", str(tmp)]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise MediaError(f"loudness pass failed: {result.stderr.strip()[-400:]}")
    tmp.replace(path)
    return round(measure_lufs(path), 1)
