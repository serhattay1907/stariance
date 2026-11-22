import { z } from "zod";
import { badgeSchema } from "../effects/Badge";
import { barChartSchema } from "../effects/BarChart";
import { checklistSchema } from "../effects/Checklist";
import { emojiPopSchema } from "../effects/EmojiPop";
import { headlineWallSchema } from "../effects/HeadlineWall";
import { labelSchema } from "../effects/Label";
import { lineChartSchema } from "../effects/LineChart";
import { numberPopSchema } from "../effects/NumberPop";
import { outroSchema } from "../effects/Outro";
import { quoteBubblesSchema } from "../effects/QuoteBubbles";
import { spotlightSchema } from "../effects/Spotlight";
import { statRowSchema } from "../effects/StatRow";
import { timelineSchema } from "../effects/Timeline";
import { titleBehindSchema } from "../effects/TitleBehind";
import { versusSchema } from "../effects/Versus";

// Turns the planned effects of an edit plan into the inputs of the effect components.
// Times in the plan are output seconds; `params` hold the content (text, numbers) the
// component takes. The mapping matches the showcase and the sound hit points in
// sounds.json, so a whip peaks, sounds and flashes on the same frame.

export const plannedEffectSchema = z.object({
  effect: z.string(),
  at: z.number().min(0),
  seconds: z.number().positive(),
  reason: z.string().default(""),
  params: z.record(z.string(), z.unknown()).default({}),
});
export type PlannedEffect = z.infer<typeof plannedEffectSchema>;
type Point = { x: number; y: number };

// Overlay effects drawn above the footage, in plan order.
export type Overlay =
  | { kind: "title"; until: number; props: z.input<typeof titleBehindSchema> }
  | { kind: "label"; until: number; props: z.input<typeof labelSchema> }
  | { kind: "emoji"; until: number; props: z.input<typeof emojiPopSchema> }
  | { kind: "number"; until: number; props: z.input<typeof numberPopSchema> }
  | { kind: "bar"; until: number; props: z.input<typeof barChartSchema> }
  | { kind: "line"; until: number; props: z.input<typeof lineChartSchema> }
  | { kind: "versus"; until: number; props: z.input<typeof versusSchema> }
  | { kind: "stats"; until: number; props: z.input<typeof statRowSchema> }
  | { kind: "quote"; until: number; props: z.input<typeof quoteBubblesSchema> }
  | { kind: "checklist"; until: number; props: z.input<typeof checklistSchema> }
  | { kind: "headlines"; until: number; props: z.input<typeof headlineWallSchema> }
  | { kind: "timeline"; until: number; props: z.input<typeof timelineSchema> }
  | { kind: "badge"; until: number; props: z.input<typeof badgeSchema> }
  | { kind: "spotlight"; until: number; props: z.input<typeof spotlightSchema> }
  | { kind: "outro"; until: number; props: z.input<typeof outroSchema> };

export type Timeline = {
  zooms: { at: number; scale: number; ease: number }[];
  whips: number[];
  shakes: number[];
  leaks: number[];
  transitions: { kind: "glitch" | "iris" | "zoomblur"; at: number }[];
  moves: { kind: "orbit" | "pullback" | "zoomthrough" | "vertigo"; at: number; seconds: number }[];
  speaker: { kind: "blur" | "swap" | "glow" | "colorpop"; at: number; seconds: number }[];
  /** Windows (output seconds) where the speaker is drawn as its own layer. */
  person: [number, number][];
  overlays: Overlay[];
  /** Captions stop here (the outro card takes the screen). */
  captionsUntil: number;
};

const num = (v: unknown, fallback: number) => (typeof v === "number" && Number.isFinite(v) ? v : fallback);

/** Every effect id the Edit composition can draw (a Python test keeps it equal to the catalog). */
export const EDIT_EFFECTS = [
  "title.behind",
  "camera.zoom",
  "camera.whip",
  "camera.shake",
  "emoji.pop",
  "number.pop",
  "transition.glitch",
  "transition.iris",
  "transition.zoomblur",
  "label",
  "grade.leak",
  "chart.bar",
  "chart.line",
  "compare.versus",
  "stats.row",
  "speaker.blur",
  "speaker.swap",
  "speaker.glow",
  "speaker.colorpop",
  "quote.bubbles",
  "list.checklist",
  "headline.wall",
  "timeline",
  "badge",
  "spotlight",
  "camera.orbit",
  "camera.pullback",
  "camera.zoomthrough",
  "camera.vertigo",
  "outro.card",
] as const;

// Validate the content up front with the component's own schema, so a bad plan fails
// with the effect and its time instead of somewhere inside a frame.
const check = <S extends z.ZodTypeAny>(schema: S, e: PlannedEffect, input: Record<string, unknown>): z.input<S> => {
  const result = schema.safeParse(input);
  if (!result.success) {
    const issue = result.error.issues[0];
    const where = issue.path.length ? `params.${issue.path.join(".")}` : "params";
    throw new Error(`Effect '${e.effect}' at ${e.at}s: ${where}: ${issue.message}`);
  }
  return input as z.input<S>;
};

export const buildTimeline = (effects: PlannedEffect[], face: Point, duration: number): Timeline => {
  const tl: Timeline = {
    zooms: [],
    whips: [],
    shakes: [],
    leaks: [],
    transitions: [],
    moves: [],
    speaker: [],
    person: [],
    overlays: [],
    captionsUntil: duration,
  };
  const sorted = [...effects].sort((a, b) => a.at - b.at);
  for (const e of sorted) {
    const p = e.params;
    const end = e.at + e.seconds;
    const timed = { ...p, at: e.at, seconds: e.seconds };
    switch (e.effect) {
      case "camera.zoom":
        tl.zooms.push({ at: e.at, scale: num(p.scale, 1.12), ease: num(p.ease, 0.15) });
        tl.zooms.push({ at: end, scale: 1, ease: 0.3 });
        break;
      case "camera.whip":
        tl.whips.push(e.at + e.seconds / 2);
        break;
      case "camera.shake":
        tl.shakes.push(e.at);
        break;
      case "grade.leak":
        tl.leaks.push(e.at + 0.1);
        break;
      case "transition.glitch":
      case "transition.iris":
        tl.transitions.push({ kind: e.effect === "transition.glitch" ? "glitch" : "iris", at: e.at + e.seconds / 2 });
        break;
      case "transition.zoomblur":
        tl.transitions.push({ kind: "zoomblur", at: e.at + 0.1 });
        break;
      case "camera.orbit":
      case "camera.pullback":
      case "camera.zoomthrough":
      case "camera.vertigo":
        tl.moves.push({ kind: e.effect.slice("camera.".length) as Timeline["moves"][number]["kind"], at: e.at, seconds: e.seconds });
        tl.person.push([e.at, end]);
        break;
      case "speaker.blur":
      case "speaker.swap":
      case "speaker.glow":
      case "speaker.colorpop":
        tl.speaker.push({ kind: e.effect.slice("speaker.".length) as Timeline["speaker"][number]["kind"], at: e.at, seconds: e.seconds });
        break;
      case "title.behind": {
        const raw = Array.isArray(p.lines) ? (p.lines as Record<string, unknown>[]) : [];
        const lines = raw.map((l, i) => ({ ...l, at: e.at + num(l.at, i * 0.4) }));
        const props = check(titleBehindSchema, e, { ...p, lines, until: end });
        tl.overlays.push({ kind: "title", until: end, props });
        tl.person.push([e.at, end]);
        break;
      }
      case "label":
        tl.overlays.push({ kind: "label", until: end + 0.2, props: check(labelSchema, e, { ...p, from: e.at, to: end }) });
        break;
      case "emoji.pop":
        tl.overlays.push({ kind: "emoji", until: end, props: check(emojiPopSchema, e, timed) });
        break;
      case "number.pop":
        tl.overlays.push({ kind: "number", until: end, props: check(numberPopSchema, e, timed) });
        break;
      case "chart.bar":
        tl.overlays.push({ kind: "bar", until: end, props: check(barChartSchema, e, timed) });
        break;
      case "chart.line":
        tl.overlays.push({ kind: "line", until: end, props: check(lineChartSchema, e, timed) });
        break;
      case "compare.versus":
        tl.overlays.push({ kind: "versus", until: end, props: check(versusSchema, e, timed) });
        break;
      case "stats.row":
        tl.overlays.push({ kind: "stats", until: end, props: check(statRowSchema, e, timed) });
        break;
      case "quote.bubbles":
        tl.overlays.push({ kind: "quote", until: end, props: check(quoteBubblesSchema, e, timed) });
        break;
      case "list.checklist":
        tl.overlays.push({ kind: "checklist", until: end, props: check(checklistSchema, e, timed) });
        break;
      case "headline.wall":
        tl.overlays.push({ kind: "headlines", until: end, props: check(headlineWallSchema, e, timed) });
        break;
      case "timeline":
        tl.overlays.push({ kind: "timeline", until: end, props: check(timelineSchema, e, timed) });
        break;
      case "badge":
        tl.overlays.push({ kind: "badge", until: end, props: check(badgeSchema, e, timed) });
        break;
      case "spotlight":
        tl.overlays.push({ kind: "spotlight", until: end, props: check(spotlightSchema, e, { x: face.x, y: face.y, ...timed }) });
        break;
      case "outro.card":
        tl.overlays.push({ kind: "outro", until: duration, props: check(outroSchema, e, { origin: face, ...p, from: e.at }) });
        tl.captionsUntil = Math.min(tl.captionsUntil, e.at);
        break;
      default:
        throw new Error(`Effect '${e.effect}' at ${e.at}s is not in the effect library; see \`stagorix effects\``);
    }
  }
  return tl;
};
