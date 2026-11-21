"""Edit: an edit plan plus your footage becomes a video.

The plan says what the viewer sees: which pieces of which recordings play in which order
(segments, in source seconds), and which effects appear when (in output seconds, after the
cuts). This module turns it into props for the `Edit` composition:

- segments are snapped to the frame grid, so picture and sound cut on the same frame;
- transcript words are moved onto the output timeline (words inside a cut are dropped);
- the voice is cut with ffmpeg (10 ms fades at every join, so cuts do not click) from the
  cleaned voice track when `stagorix analyze` wrote one;
- person mattes are made only for the seconds that need one (speaker effects, the
  title behind the speaker, camera moves with depth), in draft or final quality.

The aspect ratio is a render parameter, not part of the plan: the same plan renders
as 9:16 (from the face-tracked 9:16 cut when there is one) and 16:9 (from the original).
Staged files go to render/public/edit-input/, which is gitignored (principle 4).
"""

from __future__ import annotations

import shutil
import statistics
import subprocess
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from stagorix.analysis.media import MediaError, _ffmpeg
from stagorix.analysis.models import FaceTrack, Transcript, Word
from stagorix.render.motion import CATALOG, EditPlan, Segment, Severity, Violation, check_plan
from stagorix.render.renderer import FINAL_FPS, Quality, Renderer, RenderJob, RenderResult, fps_for
from stagorix.verify import RENDER_DIR

INPUT_DIR = RENDER_DIR / "public" / "edit-input"
FADE = 0.01
# Effects whose speaker is drawn as its own layer from a person matte.
PERSON_EFFECTS = {"title.behind"} | {
    k for k, v in CATALOG.items() if v.component in ("SpeakerFx", "CameraMove")
}


class Aspect(StrEnum):
    VERTICAL = "9:16"
    LANDSCAPE = "16:9"


SIZES = {Aspect.VERTICAL: (1080, 1920), Aspect.LANDSCAPE: (1920, 1080)}


class EditError(RuntimeError):
    """The plan cannot be rendered as it is (missing file, broken timeline)."""


class Piece(BaseModel):
    """A segment on the frame grid: source seconds [start, end) play at output second `at`."""

    source: str
    start: float
    end: float
    at: float

    @property
    def seconds(self) -> float:
        return self.end - self.start


def _snap(t: float, fps: int = FINAL_FPS) -> float:
    return round(round(t * fps) / fps, 6)


def resolve_pieces(plan: EditPlan, durations: dict[str, float]) -> list[Piece]:
    """Segments in play order, snapped to frames and clamped to each source's length."""
    if not plan.sources:
        raise EditError("the plan has no sources")
    first = plan.sources[0].id
    segments = plan.segments or [Segment(source=first, start=0, end=durations[first])]
    pieces: list[Piece] = []
    at = 0.0
    for seg in segments:
        start = _snap(seg.start)
        end = _snap(min(seg.end, durations[seg.source]))
        if end - start < 1 / FINAL_FPS:
            continue
        pieces.append(Piece(source=seg.source, start=start, end=end, at=round(at, 6)))
        at += end - start
    if not pieces:
        raise EditError("no segment is left after snapping to frames")
    return pieces


def output_duration(pieces: list[Piece]) -> float:
    return round(sum(p.seconds for p in pieces), 6)


def to_output(t: float, source: str, pieces: list[Piece]) -> float | None:
    """Output second of a source second, or None when it was cut (first match wins)."""
    for p in pieces:
        if p.source == source and p.start <= t < p.end:
            return round(p.at + t - p.start, 4)
    return None


def map_words(words: list[Word], source: str, pieces: list[Piece]) -> list[dict[str, Any]]:
    """Words on the output timeline. A word counts if its middle is kept; it is clamped to its piece."""
    out = []
    for w in words:
        mid = (w.start + w.end) / 2
        for p in pieces:
            if p.source == source and p.start <= mid < p.end:
                start = p.at + max(w.start, p.start) - p.start
                end = p.at + min(w.end, p.end) - p.start
                out.append({"text": w.text, "start": round(start, 3), "end": round(end, 3)})
                break
    out.sort(key=lambda w: w["start"])
    return out


def matte_ranges(plan: EditPlan, pieces: list[Piece]) -> dict[str, list[tuple[float, float]]]:
    """Source seconds that need a person matte, per source."""
    spans: dict[str, list[tuple[float, float]]] = {}
    for e in plan.effects:
        if e.effect not in PERSON_EFFECTS:
            continue
        a, b = e.at, e.at + e.seconds
        for p in pieces:
            lo, hi = max(a, p.at), min(b, p.at + p.seconds)
            if hi > lo:
                spans.setdefault(p.source, []).append(
                    (round(p.start + lo - p.at, 3), round(p.start + hi - p.at, 3))
                )
    return spans


def audio_filter(pieces: list[Piece], inputs: dict[str, int | None]) -> str:
    """ffmpeg filter that cuts and joins the voice; a source without audio gives silence."""
    parts, labels = [], []
    for i, p in enumerate(pieces):
        idx = inputs[p.source]
        if idx is None:
            parts.append(f"aevalsrc=0:c=stereo:s=48000:d={p.seconds:.6f}[a{i}]")
        else:
            out = max(p.seconds - FADE, 0)
            parts.append(
                f"[{idx}:a]atrim=start={p.start:.6f}:end={p.end:.6f},asetpts=PTS-STARTPTS,"
                f"aresample=48000,aformat=channel_layouts=stereo,"
                f"afade=t=in:d={FADE},afade=t=out:st={out:.6f}:d={FADE}[a{i}]"
            )
        labels.append(f"[a{i}]")
    return ";".join(parts) + ";" + "".join(labels) + f"concat=n={len(pieces)}:v=0:a=1[a]"


def focus_of(track: FaceTrack, vertical: bool) -> tuple[float, float]:
    """Median face position (0–1) in the original, or in the face-tracked 9:16 cut."""
    if not track.detections:
        return (0.5, 0.4)
    xs, ys = [], []
    for d in track.detections:
        cx, cy = d.x + d.w / 2, d.y + d.h * 0.45
        if vertical:
            left = track.crop_x[min(d.frame, len(track.crop_x) - 1)]
            xs.append((cx - left) / track.crop_width)
        else:
            xs.append(cx / track.width)
        ys.append(cy / track.height)
    clamp = lambda v: min(max(v, 0.0), 1.0)  # noqa: E731
    return (round(clamp(statistics.median(xs)), 4), round(clamp(statistics.median(ys)), 4))


class StagedSource(BaseModel):
    id: str
    footage: Path
    audio: Path | None
    width: int
    height: int
    duration: float
    focus: tuple[float, float]
    transcript: Transcript | None


def _resolve(base: Path, path: str | None) -> Path | None:
    if path is None:
        return None
    p = Path(path)
    return p if p.is_absolute() else (base / p).resolve()


def inspect_source(src, base: Path, aspect: Aspect) -> StagedSource:  # type: ignore[no-untyped-def]
    """Pick the footage for the aspect ratio and read what analysis knows about the source."""
    from stagorix.analysis.video import probe

    video = _resolve(base, src.video)
    analysis = _resolve(base, src.analysis)
    if video is None or not video.exists():
        raise EditError(f"source '{src.id}': video {video} not found")
    vertical = analysis / "vertical.mp4" if analysis else None
    use_vertical = aspect is Aspect.VERTICAL and vertical is not None and vertical.exists()
    footage = vertical if use_vertical and vertical else video
    info = probe(footage)
    original = probe(video)
    voice = analysis / "voice.wav" if analysis else None
    audio = voice if voice and voice.exists() else (video if original.has_audio else None)
    focus = (0.5, 0.4)
    if analysis and (analysis / "face_track.json").exists():
        track = FaceTrack.model_validate_json((analysis / "face_track.json").read_text(encoding="utf-8"))
        focus = focus_of(track, vertical=use_vertical)
    transcript = None
    if analysis and (analysis / "transcript.json").exists():
        transcript = Transcript.model_validate_json(
            (analysis / "transcript.json").read_text(encoding="utf-8")
        )
    return StagedSource(
        id=src.id,
        footage=footage,
        audio=audio,
        width=info.width,
        height=info.height,
        duration=round(original.frames / original.fps, 6) if original.fps else 0.0,
        focus=focus,
        transcript=transcript,
    )


def _cut_audio(pieces: list[Piece], sources: dict[str, StagedSource], out: Path) -> None:
    order = [sid for sid in dict.fromkeys(p.source for p in pieces) if sources[sid].audio]
    inputs: dict[str, int | None] = {sid: None for sid in sources}
    inputs.update({sid: i for i, sid in enumerate(order)})
    cmd = [_ffmpeg(), "-v", "error", "-y"]
    for sid in order:
        cmd += ["-i", str(sources[sid].audio)]
    cmd += ["-filter_complex", audio_filter(pieces, inputs), "-map", "[a]", "-c:a", "pcm_s16le", str(out)]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise MediaError(f"could not cut the voice: {result.stderr.strip()[-500:]}")


def build_props(
    plan: EditPlan,
    plan_dir: Path,
    aspect: Aspect = Aspect.VERTICAL,
    quality: Quality = Quality.DRAFT,
    stage_dir: Path = INPUT_DIR,
) -> dict[str, Any]:
    """Stage footage, voice and mattes under render/public and return the Edit props."""
    from stagorix.analysis.matte import Quality as MatteQuality
    from stagorix.analysis.matte import write_mattes
    from stagorix.assets.sounds import plan_cues

    sources = {s.id: inspect_source(s, plan_dir, aspect) for s in plan.sources}
    pieces = resolve_pieces(plan, {k: v.duration for k, v in sources.items()})
    if stage_dir.exists():
        shutil.rmtree(stage_dir)
    stage_dir.mkdir(parents=True)
    public = RENDER_DIR / "public"
    rel = lambda p: p.relative_to(public).as_posix() if p.is_relative_to(public) else p.name  # noqa: E731

    mattes = matte_ranges(plan, pieces)
    staged: dict[str, Any] = {}
    for sid, s in sources.items():
        if not any(p.source == sid for p in pieces):
            continue
        target = stage_dir / f"{sid}{s.footage.suffix}"
        shutil.copyfile(s.footage, target)
        entry: dict[str, Any] = {
            "footage": rel(target),
            "width": s.width,
            "height": s.height,
            "focus": {"x": s.focus[0], "y": s.focus[1]},
            "matteDir": "",
            "matteFps": FINAL_FPS,
            "matteFrames": 0,
        }
        if sid in mattes:
            q = MatteQuality.DRAFT if quality is Quality.DRAFT else MatteQuality.FINAL
            try:
                m = write_mattes(target, stage_dir / f"{sid}-matte", q, mattes[sid])
            except Exception as exc:  # model download or inference; say which step failed
                raise EditError(
                    f"person mattes ({q}) for '{sid}' failed: {str(exc).splitlines()[0][:200]}. "
                    "Speaker effects, the title behind the speaker and camera moves need them; "
                    "check the network or run inside Docker, where the models are built in."
                ) from exc
            entry.update(matteDir=rel(stage_dir / f"{sid}-matte"), matteFps=m.fps, matteFrames=m.frames)
        staged[sid] = entry

    audio = ""
    if any(s.audio for s in sources.values()):
        _cut_audio(pieces, sources, stage_dir / "voice.wav")
        audio = rel(stage_dir / "voice.wav")

    words: list[dict[str, Any]] = []
    locale = "en"
    for sid, s in sources.items():
        if s.transcript:
            words += map_words(s.transcript.words, sid, pieces)
            locale = s.transcript.language or locale
    words.sort(key=lambda w: w["start"])

    duration = output_duration(pieces)
    effects = [e.model_dump() for e in plan.effects if e.at < duration]
    return {
        "aspect": str(aspect),
        "fps": fps_for(quality),
        "duration": duration,
        "look": plan.look,
        "sources": staged,
        "pieces": [p.model_dump() for p in pieces],
        "audio": audio,
        "words": words,
        "captions": {
            "enabled": plan.captions.enabled and bool(words),
            "style": plan.captions.style,
            "position": plan.captions.position,
            "keywords": plan.captions.keywords,
            "maxWords": plan.captions.max_words,
            "locale": locale,
        },
        "effects": effects,
        "sounds": [{"sound": c.sound, "at": c.at} for c in plan_cues(plan) if c.at < duration],
    }


def blocking(found: list[Violation]) -> list[Violation]:
    return [v for v in found if v.severity is Severity.ERROR]


def render_edit(
    plan_file: Path,
    out: Path,
    aspect: Aspect = Aspect.VERTICAL,
    quality: Quality = Quality.DRAFT,
    browser: str | None = None,
    renderer: Renderer | None = None,
) -> RenderResult:
    """Check the plan, stage its media and render it. Plan errors stop the render."""
    from stagorix.render.renderer import default_renderer
    from stagorix.render.showcase import ensure_sounds

    plan = EditPlan.model_validate_json(plan_file.read_text(encoding="utf-8"))
    errors = blocking(check_plan(plan))
    if errors:
        raise EditError("the plan has errors:\n" + "\n".join(f"{v.at:.1f}s {v.message}" for v in errors))
    ensure_sounds()
    props = build_props(plan, plan_file.parent.resolve(), aspect, quality)
    out = out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    job = RenderJob(composition="Edit", out=out, props=props, quality=quality, browser=browser)
    return (renderer or default_renderer()).render(job)
