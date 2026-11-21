# Roadmap

Source of truth for progress. 12 phases after Phase 0. Tags: **(S)** = owner task (decision, approval, hardware test), **(C)** = code task.

| Phase | Name | Status |
| --- | --- | --- |
| 0 | Setup | ✅ |
| 1 | Pilot | ✅ |
| 2 | Cleanup and repo skeleton | ✅ (macOS test deferred, see 2.8) |
| 3 | Core engine | ⬜ |
| 4 | Brand system | ⬜ |
| 5 | Agents (LangGraph) | ⬜ |
| 6 | Control panel | ⬜ |
| 7 | Asset layer | ⬜ |
| 8 | Upload your own video | ⬜ |
| 9 | Publishing | ⬜ |
| 10 | Automation | ⬜ |
| 11 | First real week (first pilot brand) | ⬜ |
| 12 | Open source and CV | ⬜ |
| 13 | Native install and desktop app | ⬜ |

## Stariance MVP alignment (November 2026)

Stagorix is the open-source video engine of **Stariance**, a growth studio for brands and creators. Both live in this monorepo: the engine in `packages/stagorix/`, the app layer in `apps/stariance/`. The Stariance MVP (target: 31 December 2026) reorders this roadmap as below. Phase numbers stay; this table decides what is built now.

| MVP phase | Dates (est.) | Stagorix tasks | New work |
| --- | --- | --- | --- |
| 0 · Hygiene | before A | — | Secret scanning, attribution check, `ASSETS.md`, dependency license check, branch protection (S) |
| A · Engine bridge | 23–29 Nov | 3.6 | `Edit` composition (edit plan + footage + cuts + captions → video); aspect ratio as a parameter; renderer interface; time measurement |
| B · Brand core | 30 Nov–6 Dec | 4.1, 4.3, 8.1 | Profile = personality → style → pack; looks become styles; rule-based edit v0 |
| C · Brain + assembly | 7–13 Dec | 5.1, 5.5, 5.6, 6.1 | Multi-clip assembly (order, best take, audio/colour matching) |
| D · Format range | 14–20 Dec | 8.2, 8.4 | 16:9 (three base layouts first, own safe area), cover image (strongest settled frame, also placed at frame 0), share text (1–3 sentences) |
| E · App layer | 21–27 Dec | 4.2, 6.2–6.4 | In `apps/stariance/`: wizard, pack recommendation, approval, preview, before/after, basic Insight |
| F · Quality and release | 28–31 Dec | 4.6, 8.5, 12.1 | First pack set (~10 styles), 12 format cards, quality gates v1 with a quality report, Docker install, demo |
| R · Research (parallel) | 30 Nov–20 Dec | 5.8 (narrowed) | 12 format cards with data, brand growth rules |

Later: 3.5b, 4.4, phase 7, 9, 10, 11, 13. Dropped from the MVP: news agents 5.2–5.4. The counts under Option targets are upper bounds for later releases, not goals: the MVP aims at quality (12 core formats, about 10 crafted styles).

Ideas from the source review (project docs, not scheduled): plan file with storyboard timings and beat-aligned cuts, sound metadata for automatic sound choice (brightness, high-frequency risk, transient), music beat analysis, model router with a semantic cache, trend research for Insight, a product or site launch pack.

## Milestones

| Milestone | What the user gets | Done when |
| --- | --- | --- |
| **MVP** (31 Dec 2026) | From the brand wizard to a first video in the panel: own clips, a long recording or a finished video → cut, captioned, branded video in 9:16 and 16:9 with cover and text, pack recommendation, approval, preview, before/after, basic Insight | MVP phases 0, A–F and R above |
| **v1** | Every option dimension at its v1 target, three-layer choice, option review gate passed | End of phase 8 (8.5) |
| **Pro** | Every option dimension at its Pro target, publishing and automation | End of phase 12 |

## Option targets

The user chooses from a rich, curated catalog; nothing is locked (filters are a default view with "show all", expert mode shows everything, every choice can be undone). Exact lists are researched and approved in the task that builds them.

| Dimension | v1 | Pro | Task |
| --- | --- | --- | --- |
| Content formats | 12 (core) | 25+ | 5.8 |
| Hook types | 20 | 30+ | 5.8 |
| Looks (style packs) | 10 | 15+ | 4.3 |
| Font pairs (OFL) | 20 | 30+ | 4.6 |
| Caption styles | 15 | 20+ | 3.3 |
| Effects | 40 | 60+ | 3.3–3.5 |
| Layouts | 10 | 12+ | 3.4 |
| Sound effects (curated, licensed) | ~150 in 12 categories | 300+ | 3.3c-4, 7.3 |
| Music | 12 moods × 5 tracks | 20+ moods | 7.4 |
| Voice-over | Local free TTS, 2–4 voices per language | + paid voice cloning plugin (off, budget cap, own voice only) | 7.6 |
| Visual sources | Own files, stock B-roll, Lottie, import with license field | + AI generation plugins (off, budget cap) | 7.1–7.5, 7.7 |
| Duration | 15 / 30 / 45 / 60 / 90 s / 3 min | per platform rules | 8.4 |
| Tempo | 3 levels | 5 levels | 8.4 |
| Calls to action | 12 types | 20+ | 9.4 |

After the option review gate, requests stay open for good: each wish becomes a numbered request (E-01, E-02, …) delivered as one small PR.

## Phase 0 — Setup ✅

- [x] 0.1 GitHub repo (C)
- [x] 0.2 Docker installed and tested (C)
- [x] 0.3 Git, Node, Python, uv (S)
- [x] 0.4 Dev tooling + token (S)
- [x] 0.5 Notion connection + token (C, token S)
- [x] 0.6 Drive `inbox` / `output` folders (C)
- [x] 0.7 Repo connected to the session (C)

## Phase 1 — Pilot ✅

- [x] 1.1 Silent news pilot (C)
- [x] 1.2 Raw video to effect-rich edit v1 (C)
- [x] 1.3 Review: flow is good; visual richness and audio quality need work (S)

## Phase 2 — Cleanup and repo skeleton

- [x] 2.1 Rename repo to `stagorix` (C)
- [x] 2.2 Separate "Stagorix" workspace with the principles written down (S)
- [x] 2.3 `CONTRIBUTING.md`, `README`, `docs/ARCHITECTURE`, `DECISIONS`, `ROADMAP` (C, push approval S)
- [x] 2.4 Folder structure, `pyproject.toml`, `package.json`, CLI skeleton (C)
- [x] 2.5 Docker `cpu` / `gpu` profiles, pinned versions, fonts and models in the image (C)
- [x] 2.6 Golden test (`stagorix verify`) + CI (C)
- [x] 2.7 Official Remotion skills: documented local install, not vendored (C)
- [ ] 2.8 Install test on macOS, Windows and Linux (S) — Windows ✅ (Docker, golden test SSIM 1.0), Linux ✅ (CI); **macOS open: required before 12.1**

## Phase 3 — Core engine

- [x] 3.1 Analysis: Whisper, face tracking, person cutout (ported from pilot) (C)
- [x] 3.2 Flub detector (C) — 3.2a detection + confidence list, 3.2b terminal approval + cut preview
- [x] 3.3 Effect library v1: pilot effects as Zod-typed components (C)
  - [x] 3.3a Talking-head effects on a theme scale: captions (5 styles), title behind speaker + cutout layer, camera zooms and whips, label, outro, grade; bundled fonts; named positions in a safe area; `Showcase` composition and `stagorix showcase`
  - [x] 3.3b Motion language: effect roles, intensity and spacing rules, set per brand (`docs/MOTION.md`, `stagorix effects`, `stagorix check-plan`)
  - [x] 3.3c Pack A
    - [x] 3.3c-1 Caption styles bold, reveal, marker; emoji pop; number pop; camera shake
    - [x] 3.3c-2 Transitions: glitch, iris (mask), zoom blur; showcase over your own footage (`--footage`)
    - [x] 3.3c-3 Ten looks (`stagorix looks`, `showcase --look`, look reel); five more OFL fonts
    - [x] 3.3c-4 Sound library: 149 sounds in 12 categories (49 synthesized, 100 Kenney CC0) with a license log, a default sound per effect, one sound per beat, `stagorix sounds`
  - [x] 3.3d Pack B
    - [x] 3.3d-1 Data cards: bar chart, line chart, A vs B, stat row (role info; numbers in the brand's locale)
    - [x] 3.3d-2 Speaker effects: background blur, background swap, outline glow, colour pop; person mattes in two qualities (`stagorix matte`: draft with MediaPipe selfie segmentation, final with U²-Net), only for the effect's seconds
  - [x] 3.3e Cards from the pilot: quote bubbles, checklist, headline wall, timeline, badge, spotlight
- [x] 3.4 Layouts: 10 for v1 (C)
  - [x] 3.4a Full face, split screen, card over face, inside a phone, picture in picture (`stagorix layouts`, layout reel)
  - [x] 3.4b B-roll with the face in a corner, background swap, reaction (clip with credit), screen recording with the face, text only
- [ ] 3.5 New effects: list cards, progress bar, phone mock-up, orbit, pull-back, zoom-through, vertigo, UI/diagram scenes, logo stack (logos supplied by the user, none bundled), word-synced kinetic typography (C)
  - [x] 3.5a Camera moves: orbit, pull-back, zoom-through, vertigo (depth layers: background and speaker move separately)
  - [ ] 3.5b Progress bar, UI/diagram scene, logo stack, word-synced kinetic typography
- [ ] 3.6 Draft render for previews (540p, lower frame rate, ~4× faster on CPU) and final render only after approval, −14 LUFS; a thin renderer interface so Remotion can be swapped (C); time analysis, draft and final render on a 60 s clip and log the result in `DECISIONS.md` (C)

## Phase 4 — Brand system

- [ ] 4.1 Brand profile schema (`brand.yaml`, `sources.yaml`, `tokens.json`, `motion-system.md`) and the option catalog with brand defaults (C)
  - Rule history: every change to the profile is recorded with its source (style card, variant pick, user feedback, retention data) and can be undone
  - Learning mode per brand: suggest automatically / ask every time / off
  - Include per-language filler words (e.g. "um", "ııı") passed to Whisper as a hint, so fillers are transcribed and cut instead of hiding inside a neighbouring word
- [ ] 4.2 Brand setup wizard, after 4.4 (C). First step offers three paths: learn from videos you like (4.4), pick a ready-made look, or expert mode; every step can be skipped
- [ ] 4.3 Looks (style packs): 10 built in 3.3c-3; toward 15+ with a style catalogue drawn from `docs/REFERENCES.md` (C), approval (S)
- [ ] 4.4 Style card from reference videos (`extract-style`), moved before 4.2 (C), first references (S)
  - Measures cut tempo, speech rate, pauses, zoom frequency and strength, caption position/case/words per line, accent colour, closest bundled font; each value with a confidence, shown for approval and written as profile defaults
  - Reference videos are the user's own files and stay local (only measured parameters are stored); optional download (yt-dlp) is opt-in and at the user's own responsibility
- [ ] 4.5 First profile: the first pilot brand (S provides brand info, C sets it up)
- [ ] 4.6 Font pairs: 20 OFL pairs with Latin Extended support (C), selection (S)

## Phase 5 — Agents (LangGraph)

- [ ] 5.1 LLM adapters (C)
- [ ] 5.2 Scout + deduplication (C), source list (S)
- [ ] 5.3 Scorer (C), score approval on 20 samples (S)
- [ ] 5.4 Writer + verify/rewrite loop (C), tone approval (S)
- [ ] 5.5 Editor agent (edit plan) (C); free-text feedback ("too many zooms") becomes a proposed profile change, applied only after approval
- [ ] 5.6 Visual QA agent (`qa-frames`) with a scoring rubric (C)
- [ ] 5.7 Project skills: `edit-raw-video`, `news-short`, `extract-style`, `qa-frames` (C)
- [ ] 5.8 Format library: 12 core formats as cards (structure, hook, sample videos, sources), more later (C), approval (S)

## Phase 6 — Control panel

- [ ] 6.1 Run and event log (every step, duration, tokens, cost) (C)
- [ ] 6.2 Panel: job list, live agent stream, stop / retry (C)
- [ ] 6.3 Approval screen: edit plan, preview, publish approval; variant pick (2–3 draft openings with different hook, look or tempo; the choice feeds the profile; can be turned off) (C)
- [ ] 6.4 Brand wizard and settings in the panel; three-layer choice (one-click pack, guided wizard, expert mode), compatibility filter with "show all", search and favourites (C)
- [ ] 6.5 Optional Notion sync + mobile notifications (C)
- [ ] 6.6 Optional Langfuse connection (C)
- [ ] 6.7 Interface in Turkish and English (i18n; one translation file per language), chosen separately from content language (C)

## Phase 7 — Asset layer

- [ ] 7.1 Own files (`assets/`) + priority rule (C)
- [ ] 7.2 Pexels, Pixabay, Mixkit, Lottie clients + license log (C)
- [ ] 7.3 Sound library to 300+ (more CC0 packs: Kenney impact, digital, sci-fi; hand-picked Freesound CC0) + selection with `stagorix sounds reel` (C), selection (S)
- [ ] 7.4 Music options; cuts and effects snapped to the beat (C), selection (S)
- [ ] 7.5 `Generator` interface + AI generation plugins (Higgsfield and others), off by default, budget cap (C)
- [ ] 7.6 Voice-over: local free TTS (Piper); optional paid voice cloning plugin, off, own voice only (C)
- [ ] 7.7 Import any asset (image, video, audio, voice) with a required license field (C)

## Phase 8 — Upload your own video

- [ ] 8.1 `edit` and `polish` modes (C); `stagorix feedback`: structured feedback (tempo, zoom, effect density, caption size) becomes a profile change for this video or always
- [ ] 8.2 `clip` mode (C)
- [ ] 8.3 Test with own videos (S)
- [ ] 8.4 Duration and tempo presets (C)
- [ ] 8.5 Option review gate: every option tried on real videos, each marked keep / fix / remove (S); v1 milestone

## Phase 9 — Publishing

- [ ] 9.1 Platform layer: YouTube and Instagram profiles (C)
- [ ] 9.2 YouTube: Google Cloud project + OAuth (S), approved upload (C)
- [ ] 9.3 Instagram: app permission (S), temporary hosting + approved publish (C)
- [ ] 9.4 Calls to action: 12 types (C)

## Phase 10 — Automation

- [ ] 10.1 Scheduler (local cron + GitHub Actions) (C)
- [ ] 10.2 Secrets (S)
- [ ] 10.3 End-to-end test (S + C)

## Phase 11 — First real week (first pilot brand)

- [ ] 11.1 Produce and publish 3 videos (S + C)
- [ ] 11.2 Fix issues (C)
- [ ] 11.3 Metrics and token/time measurement (S + C)
- [ ] 11.4 Retention data: map audience drop-offs to effects and tempo, suggest motion-rule changes per brand (approval required) (C)

## Phase 12 — Open source and CV

- [ ] 12.0 Gate: macOS install test from 2.8 passes (S); renderer review: Remotion license for companies vs. HyperFrames (Apache-2.0) maturity, decide whether to add or switch (C)
- [ ] 12.1 README, screenshots, demo GIF (C, GIF S)
- [ ] 12.2 Scoring evaluation report (C)
- [ ] 12.3 DaVinci export, optional (C)
- [ ] 12.4 CV and LinkedIn copy (C)

## Phase 13 — Native install and desktop app

- [ ] 13.1 Native install script with dependency checks on macOS, Windows and Linux; Docker optional and test-only (C)
- [ ] 13.2 macOS and Windows CI run the native install step for step, then structural golden checks (C)
- [ ] 13.3 Desktop app with a setup wizard on the same core as the CLI (C)
- [ ] 13.4 Real install test on each OS (S)
