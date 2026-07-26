/**
 * Design tokens — single source of truth for Northstar Wealth.
 *
 * Both consumed directly in TS (when needed) and projected to CSS vars in
 * `index.css`. Keep the two in sync: any new token added here must show up
 * in the :root block.
 */

export const colors = {
  // Deep neutral blue — body, phone interior, dark surfaces.
  navy: "#0B2033",
  navySoft: "#102F43",
  navyEdge: "#061522",

  // Cream — artifact cards, hero takeover.
  cream: "#F7F2EA",
  creamDeep: "#EBE3D5",

  // Fresh mint — orb glow, plan number, and CTAs.
  champagne: "#58D6B1",
  champagneSoft: "#9DEBD3",

  // Positive / negative signals.
  green: "#3D7C57",
  greenSoft: "#5FA078",
  amber: "#C9772A",

  // Ink — for cream surfaces.
  ink: "#1A1F2E",
  inkSoft: "#5D6478",

  // Light text for dark surfaces.
  ivory: "#F4FBF8",
  ivorySoft: "rgba(244, 251, 248, 0.72)",
  ivoryHairline: "rgba(157, 235, 211, 0.12)",

  // Orb moods.
  orbIdle: "#B9F5E3",
  orbListening: "#D8FAF0",
  orbTalking: "#58D6B1",
  orbPaused: "#52716F",
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
