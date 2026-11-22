import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from stagorix.analysis.models import FaceDetection, FaceTrack, Word
from stagorix.render.edit import (
    PERSON_EFFECTS,
    EditError,
    Piece,
    audio_filter,
    focus_of,
    map_words,
    matte_ranges,
    output_duration,
    resolve_pieces,
    to_output,
)
from stagorix.render.motion import CATALOG, EditPlan, PlannedEffect, Segment, Source, check_plan
from stagorix.render.renderer import DRAFT_FPS, FINAL_FPS, Quality, fps_for

ROOT = Path(__file__).resolve().parents[1]


def edit_plan(segments: list[tuple[float, float]], *effects: tuple[str, float, float]) -> EditPlan:
    return EditPlan(
        duration=sum(b - a for a, b in segments) or 1,
        sources=[Source(video="raw.mp4")],
        segments=[Segment(start=a, end=b) for a, b in segments],
        effects=[PlannedEffect(effect=e, at=a, seconds=s, reason="test") for e, a, s in effects],
    )


def test_pieces_play_in_order_on_the_frame_grid() -> None:
    plan = edit_plan([(0.0, 1.01), (2.0, 3.5)])
    pieces = resolve_pieces(plan, {"main": 10})
    assert [(p.start, p.end, p.at) for p in pieces] == [(0.0, 1.0, 0.0), (2.0, 3.5, 1.0)]
    assert output_duration(pieces) == 2.5
    for p in pieces:
        assert abs(p.start * FINAL_FPS - round(p.start * FINAL_FPS)) < 1e-6


def test_no_segments_means_the_whole_source() -> None:
    plan = EditPlan(duration=4, effects=[], sources=[Source(video="raw.mp4")])
    assert resolve_pieces(plan, {"main": 4.0}) == [Piece(source="main", start=0, end=4.0, at=0)]


def test_segments_are_clamped_to_the_source() -> None:
    pieces = resolve_pieces(edit_plan([(1, 9)]), {"main": 5.0})
    assert pieces[0].end == 5.0


def test_a_plan_without_sources_cannot_render() -> None:
    with pytest.raises(EditError):
        resolve_pieces(EditPlan(duration=1, effects=[]), {})


def test_segments_must_name_known_sources() -> None:
    with pytest.raises(ValidationError):
        EditPlan(
            duration=1, effects=[], sources=[Source(video="a.mp4")], segments=[Segment(source="b", end=1)]
        )
    with pytest.raises(ValidationError):
        Segment(start=2, end=1)


def test_cut_seconds_have_no_output_time() -> None:
    pieces = resolve_pieces(edit_plan([(0, 1), (2, 3)]), {"main": 10})
    assert to_output(0.5, "main", pieces) == 0.5
    assert to_output(1.5, "main", pieces) is None
    assert to_output(2.25, "main", pieces) == 1.25


def test_words_follow_the_cuts() -> None:
    pieces = resolve_pieces(edit_plan([(0, 1), (2, 3)]), {"main": 10})
    words = [
        Word(text="kept", start=0.1, end=0.4, probability=1),
        Word(text="cut", start=1.2, end=1.6, probability=1),
        Word(text="edge", start=1.9, end=2.3, probability=1),  # middle 2.1 is kept; clamped to 2.0
    ]
    got = map_words(words, "main", pieces)
    assert got == [
        {"text": "kept", "start": 0.1, "end": 0.4},
        {"text": "edge", "start": 1.0, "end": 1.3},
    ]


def test_mattes_only_for_person_effects_in_source_seconds() -> None:
    plan = edit_plan([(0, 1), (5, 8)], ("title.behind", 0.2, 1.3), ("label", 2, 1), ("speaker.blur", 2, 1.5))
    pieces = resolve_pieces(plan, {"main": 10})
    assert matte_ranges(plan, pieces) == {"main": [(0.2, 1.0), (5.0, 5.5), (6.0, 7.5)]}


def test_person_effects_cover_speaker_title_and_camera_moves() -> None:
    assert {"title.behind", "speaker.swap", "camera.vertigo"} <= PERSON_EFFECTS
    assert "label" not in PERSON_EFFECTS


def test_audio_joins_fade_and_silent_sources_stay_in_sync() -> None:
    pieces = [Piece(source="a", start=0, end=1, at=0), Piece(source="b", start=0, end=0.5, at=1)]
    graph = audio_filter(pieces, {"a": 0, "b": None})
    assert "[0:a]atrim=start=0.000000:end=1.000000" in graph
    assert "afade=t=out:st=0.990000:d=0.01" in graph
    assert "aevalsrc=0:c=stereo:s=48000:d=0.500000[a1]" in graph
    assert graph.endswith("concat=n=2:v=0:a=1[a]")


def test_focus_from_face_track() -> None:
    track = FaceTrack(
        source="raw.mp4",
        width=1920,
        height=1080,
        fps=30,
        frames=3,
        sample_every=1,
        detections=[FaceDetection(frame=0, x=1100, y=200, w=200, h=200, score=0.9)],
        face_ratio=1,
        crop_width=608,
        crop_x=[900.0, 900.0, 900.0],
    )
    assert focus_of(track, vertical=False) == (0.625, 0.2685)
    assert focus_of(track, vertical=True) == (round(300 / 608, 4), 0.2685)


def test_timeline_must_match_the_plan_duration() -> None:
    plan = edit_plan([(0, 2)])
    plan.duration = 5
    assert "timeline" in [v.rule for v in check_plan(plan)]


def test_draft_renders_at_a_lower_frame_rate() -> None:
    assert fps_for(Quality.DRAFT) == DRAFT_FPS < fps_for(Quality.FINAL) == FINAL_FPS


def test_every_catalog_effect_is_drawn_by_the_edit_composition() -> None:
    source = (ROOT / "render/src/compositions/editPlan.ts").read_text(encoding="utf-8")
    block = source.split("EDIT_EFFECTS = [", 1)[1].split("]", 1)[0]
    drawn = set(re.findall(r'"([a-z.]+)"', block))
    assert drawn == set(CATALOG), f"catalog vs Edit: {set(CATALOG) ^ drawn}"


def test_sample_edit_plan_is_valid() -> None:
    text = (ROOT / "examples/plans/edit-sample.json").read_text(encoding="utf-8")
    plan = EditPlan.model_validate_json(text)
    assert plan.sources and plan.segments
    assert [v for v in check_plan(plan) if v.severity == "error"] == []


def test_bench_plan_is_valid_for_any_clip_length() -> None:
    from stagorix.bench import bench_plan

    for seconds in (10, 60):
        plan = bench_plan(seconds)
        assert [v for v in check_plan(plan) if v.severity == "error"] == []
        assert all(e.at < seconds for e in plan.effects)
