import { useEffect, useMemo } from "react";
import {
  AbsoluteFill,
  type CalculateMetadataFunction,
  continueRender,
  delayRender,
  Html5Audio,
  OffthreadVideo,
  Sequence,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { z } from "zod";
import { Badge } from "../effects/Badge";
import { BarChart } from "../effects/BarChart";
import { Camera, WhipFlash } from "../effects/Camera";
import { MoveLayer, ZoomThroughFlash } from "../effects/CameraMove";
import { Captions } from "../effects/Captions";
import { Checklist } from "../effects/Checklist";
import { EmojiPop } from "../effects/EmojiPop";
import { Grade } from "../effects/Grade";
import { HeadlineWall } from "../effects/HeadlineWall";
import { Label } from "../effects/Label";
import { LineChart } from "../effects/LineChart";
import { NumberPop } from "../effects/NumberPop";
import { Outro } from "../effects/Outro";
import { QuoteBubbles } from "../effects/QuoteBubbles";
import { SpeakerBackdrop, SpeakerPerson } from "../effects/SpeakerFx";
import { Spotlight } from "../effects/Spotlight";
import { StatRow } from "../effects/StatRow";
import { Timeline as TimelineCard } from "../effects/Timeline";
import { TitleBehind } from "../effects/TitleBehind";
import { Transitions } from "../effects/Transition";
import { Versus } from "../effects/Versus";
import { Sfx, soundCueSchema } from "../sound/Sfx";
import { positionSchema } from "../theme/layout";
import { LOOKS } from "../theme/looks";
import { captionStyleSchema, ThemeProvider, themeSchema, neutralTheme } from "../theme/theme";
import { buildTimeline, type Overlay, plannedEffectSchema, type Timeline } from "./editPlan";

// Edit: your footage, cut by the plan, with captions, effects and sound on top.
// `stagorix render <plan>` stages the media and fills these props; the aspect ratio and the
// frame rate are props, so one plan renders as 9:16 or 16:9, as a draft or a final.
export const ASPECTS = { "9:16": { width: 1080, height: 1920 }, "16:9": { width: 1920, height: 1080 } } as const;

const sourceSchema = z.object({
  footage: z.string().describe("Video in render/public"),
  width: z.number().int().positive(),
  height: z.number().int().positive(),
  focus: z.object({ x: z.number().min(0).max(1), y: z.number().min(0).max(1) }).describe("Face position, 0–1"),
  matteDir: z.string().default("").describe("Person mattes (one PNG per source frame); empty = none"),
  matteFps: z.number().positive().default(30),
  matteFrames: z.number().int().min(0).default(0),
});
const pieceSchema = z.object({
  source: z.string(),
  start: z.number().min(0).describe("Source seconds"),
  end: z.number().positive(),
  at: z.number().min(0).describe("Output seconds where the piece starts"),
});
export const editSchema = z.object({
  aspect: z.enum(["9:16", "16:9"]).default("9:16"),
  fps: z.number().int().min(1).max(60).default(30),
  duration: z.number().positive().default(3),
  theme: themeSchema.default(neutralTheme),
  look: z.string().default("").describe("Ready-made look id (overrides theme)"),
  sources: z.record(z.string(), sourceSchema).default({}),
  pieces: z.array(pieceSchema).default([]),
  audio: z.string().default("").describe("Cut voice track in render/public"),
  words: z.array(z.object({ text: z.string(), start: z.number(), end: z.number() })).default([]),
  captions: z
    .object({
      enabled: z.boolean().default(true),
      style: captionStyleSchema.nullish(),
      position: positionSchema.nullish(),
      keywords: z.array(z.string()).default([]),
      maxWords: z.number().int().min(1).max(6).default(3),
      locale: z.string().default("en"),
    })
    .default({ enabled: true, keywords: [], maxWords: 3, locale: "en" }),
  effects: z.array(plannedEffectSchema).default([]),
  sounds: z.array(soundCueSchema).default([]),
});
export type EditProps = z.input<typeof editSchema>;

export const editMetadata: CalculateMetadataFunction<EditProps> = ({ props }) => {
  const p = editSchema.parse(props);
  return { ...ASPECTS[p.aspect], fps: p.fps, durationInFrames: Math.max(1, Math.ceil(p.duration * p.fps - 1e-6)) };
};

type Source = z.infer<typeof sourceSchema>;
type Piece = z.infer<typeof pieceSchema>;

/** Where the face lands in the frame: with object-fit cover and object-position at the
 *  focus, a point at focus (fx, fy) of the footage is drawn at (fx·W, fy·H). */
const faceOf = (s: Source | undefined, width: number, height: number) =>
  s ? { x: s.focus.x * width, y: s.focus.y * height } : { x: width / 2, y: height * 0.4 };

const fit = (s: Source): React.CSSProperties => ({
  width: "100%",
  height: "100%",
  objectFit: "cover",
  objectPosition: `${s.focus.x * 100}% ${s.focus.y * 100}%`,
});

/** Each piece of the plan as its own sequence, trimmed from its source. */
const Pieces: React.FC<{ pieces: Piece[]; render: (piece: Piece, source: Source) => React.ReactNode; sources: Record<string, Source> }> = ({
  pieces,
  render,
  sources,
}) => {
  const { fps } = useVideoConfig();
  return (
    <>
      {pieces.map((p, i) => {
        const from = Math.round(p.at * fps);
        const to = Math.round((p.at + p.end - p.start) * fps);
        const s = sources[p.source];
        if (!s || to <= from) return null;
        return (
          <Sequence key={i} from={from} durationInFrames={to - from}>
            {render(p, s)}
          </Sequence>
        );
      })}
    </>
  );
};

const Clip: React.FC<{ piece: Piece; source: Source }> = ({ piece, source }) => {
  const { fps } = useVideoConfig();
  return <OffthreadVideo src={staticFile(source.footage)} trimBefore={Math.round(piece.start * fps)} muted style={fit(source)} />;
};

/** Waits for a mask image before the frame is taken, so no frame renders without it. */
const useLoaded = (src: string) => {
  const handle = useMemo(() => delayRender(`mask ${src}`), [src]);
  useEffect(() => {
    const img = new Image();
    const done = () => continueRender(handle);
    img.onload = done;
    img.onerror = done; // a missing matte hides the layer; the footage below still shows
    img.src = src;
  }, [handle, src]);
};

/** The speaker alone: the clip under its person matte (white = person). */
const PersonClip: React.FC<{ piece: Piece; source: Source }> = ({ piece, source }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = piece.start + frame / fps;
  const index = Math.min(Math.floor(t * source.matteFps + 1e-6), Math.max(source.matteFrames - 1, 0));
  const src = staticFile(`${source.matteDir}/${String(index).padStart(5, "0")}.png`);
  useLoaded(src);
  const pos = `${source.focus.x * 100}% ${source.focus.y * 100}%`;
  return (
    <AbsoluteFill style={{ maskImage: `url(${src})`, maskMode: "luminance", maskSize: "cover", maskPosition: pos, maskRepeat: "no-repeat" }}>
      <Clip piece={piece} source={source} />
    </AbsoluteFill>
  );
};

/** Shows its children only inside the given windows (output seconds). */
const During: React.FC<{ windows: [number, number][]; children: React.ReactNode }> = ({ windows, children }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  return windows.some(([a, b]) => t >= a && t <= b) ? <>{children}</> : null;
};

const OverlayView: React.FC<{ o: Overlay }> = ({ o }) => {
  switch (o.kind) {
    case "title":
      return <TitleBehind {...o.props} />;
    case "label":
      return <Label {...o.props} />;
    case "emoji":
      return <EmojiPop {...o.props} />;
    case "number":
      return <NumberPop {...o.props} />;
    case "bar":
      return <BarChart {...o.props} />;
    case "line":
      return <LineChart {...o.props} />;
    case "versus":
      return <Versus {...o.props} />;
    case "stats":
      return <StatRow {...o.props} />;
    case "quote":
      return <QuoteBubbles {...o.props} />;
    case "checklist":
      return <Checklist {...o.props} />;
    case "headlines":
      return <HeadlineWall {...o.props} />;
    case "timeline":
      return <TimelineCard {...o.props} />;
    case "badge":
      return <Badge {...o.props} />;
    case "spotlight":
      return <Spotlight {...o.props} />;
    case "outro":
      return <Outro {...o.props} />;
  }
};

/** Overlays mounted only until they end, so a finished effect costs nothing. */
const Overlays: React.FC<{ items: Overlay[]; fps: number }> = ({ items, fps }) => (
  <>
    {items.map((o, i) => (
      <Sequence key={i} durationInFrames={Math.max(1, Math.ceil(o.until * fps) + 1)} layout="none">
        <OverlayView o={o} />
      </Sequence>
    ))}
  </>
);

const Scene: React.FC<z.infer<typeof editSchema> & { tl: Timeline }> = ({ sources, pieces, words, captions, tl }) => {
  const { fps, width, height } = useVideoConfig();
  const main = sources[pieces[0]?.source];
  const face = faceOf(main, width, height);
  const camera = { origin: face, zooms: tl.zooms, whips: tl.whips, shakes: tl.shakes };
  const matted = pieces.some((p) => sources[p.source]?.matteDir);
  const titles = tl.overlays.filter((o) => o.kind === "title");
  const rest = tl.overlays.filter((o) => o.kind !== "title");
  const person = (
    <Pieces pieces={pieces} sources={sources} render={(p, s) => (s.matteDir ? <PersonClip piece={p} source={s} /> : null)} />
  );
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <Transitions items={tl.transitions} origin={face}>
        <Camera {...camera}>
          <MoveLayer items={tl.moves} origin={face} layer="background">
            <SpeakerBackdrop items={tl.speaker}>
              <Pieces pieces={pieces} sources={sources} render={(p, s) => <Clip piece={p} source={s} />} />
            </SpeakerBackdrop>
          </MoveLayer>
        </Camera>
        <Overlays items={titles} fps={fps} />
        {matted && (
          <Camera {...camera}>
            <MoveLayer items={tl.moves} origin={face} layer="person">
              <SpeakerPerson items={tl.speaker}>{person}</SpeakerPerson>
              <During windows={tl.person}>{person}</During>
            </MoveLayer>
          </Camera>
        )}
        <Overlays items={rest} fps={fps} />
        {captions.enabled && words.length > 0 && (
          <Sequence durationInFrames={Math.max(1, Math.round(tl.captionsUntil * fps))} layout="none">
              <Captions
              words={words.filter((w) => w.start < tl.captionsUntil)}
              keywords={captions.keywords}
              locale={captions.locale}
              maxWords={captions.maxWords}
              style={captions.style ?? undefined}
              position={captions.position ?? undefined}
            />
          </Sequence>
        )}
      </Transitions>
      <Grade leaks={tl.leaks} progress={false} />
      <WhipFlash whips={tl.whips} />
      <ZoomThroughFlash items={tl.moves} />
    </AbsoluteFill>
  );
};

export const Edit: React.FC<EditProps> = (raw) => {
  const props = editSchema.parse(raw);
  const { width, height } = useVideoConfig();
  const main = props.sources[props.pieces[0]?.source];
  const face = faceOf(main, width, height);
  const tl = useMemo(() => buildTimeline(props.effects, face, props.duration), [props.effects, face.x, face.y, props.duration]);
  const theme = props.look in LOOKS ? LOOKS[props.look as keyof typeof LOOKS].theme : props.theme;
  return (
    <ThemeProvider value={theme}>
      <Scene {...props} tl={tl} />
      {props.audio && <Html5Audio src={staticFile(props.audio)} />}
      <Sfx cues={props.sounds} />
    </ThemeProvider>
  );
};
