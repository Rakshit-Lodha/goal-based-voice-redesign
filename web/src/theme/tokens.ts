/**
 * Design tokens — single source of truth for the affluent redesign.
 *
 * Both consumed directly in TS (when needed) and projected to CSS vars in
 * `index.css`. Keep the two in sync: any new token added here must show up
 * in the :root block.
 */

export const colors = {
  // Navy chrome — body, phone interior, dark surfaces.
  navy: "#0A1628",
  navySoft: "#161E2E",
  navyEdge: "#1F2940",

  // Cream — artifact cards, hero takeover.
  cream: "#F7F2EA",
  creamDeep: "#EBE3D5",

  // Champagne — the single warm accent. Orb glow, plan number, CTAs.
  champagne: "#C9A961",
  champagneSoft: "#E1C589",

  // Positive / negative signals.
  green: "#3D7C57",
  greenSoft: "#5FA078",
  amber: "#C9772A",

  // Ink — for cream surfaces.
  ink: "#1A1F2E",
  inkSoft: "#5D6478",

  // Ivory — for navy surfaces.
  ivory: "#F5EDDB",
  ivorySoft: "rgba(245, 237, 219, 0.62)",
  ivoryHairline: "rgba(245, 237, 219, 0.08)",

  // Orb moods.
  orbIdle: "#5B7B9C",
  orbListening: "#7AA7D4",
  orbTalking: "#D4B66E",
  orbPaused: "#3D4A5E",
} as const;

export const fonts = {
  display: "'Fraunces', 'Iowan Old Style', 'Apple Garamond', Georgia, serif",
  body: "'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
} as const;

/**
 * Type scale, in px. Sized for the 390-wide phone viewport.
 * `hero` is the plan reveal number; `display` is splash; the rest are UI.
 */
export const fontSizes = {
  hero: 84,
  display: 40,
  h1: 28,
  h2: 22,
  body: 17,
  ui: 15,
  caption: 13,
  micro: 11,
} as const;

export const motion = {
  // Premium easing — long, decisive, never bouncy.
  easeOut: "cubic-bezier(0.22, 1, 0.36, 1)",
  easeInOut: "cubic-bezier(0.65, 0, 0.35, 1)",

  // Durations, in ms. Phase 9 polish enforces ≥600ms on summon/dismiss.
  durFast: 200,
  durMed: 600,
  durSlow: 900,
} as const;

export const layout = {
  phoneWidth: 390,
  phoneHeight: 844,
  phoneRadius: 28,
} as const;

export type Tokens = {
  colors: typeof colors;
  fonts: typeof fonts;
  fontSizes: typeof fontSizes;
  motion: typeof motion;
  layout: typeof layout;
};

export const tokens: Tokens = { colors, fonts, fontSizes, motion, layout };
