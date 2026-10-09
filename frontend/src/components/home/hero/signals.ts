// The few things the page tells the WebGL scene, kept in a plain mutable object so they cost no React renders.
export type HeroSignals = {
  /** 0..1, set to 1 when the example question changes: another number rings. Decays inside the scene. */
  gust: number;
  /** Set when a question is sent: the scene closes in on this point (client px) over `ms`. */
  swirl: { x: number; y: number; ms: number } | null;
  /** True once the canvas has drawn its first frame. */
  ready: boolean;
};

export const createSignals = (): HeroSignals => ({ gust: 0, swirl: null, ready: false });

/** What Hero.tsx passes the lazily loaded scene. */
export type SceneProps = {
  signals: HeroSignals;
  /** Reduced motion: draw one still frame. */
  still: boolean;
  /** The panel is on screen and the tab is visible: animate only while true. */
  running: boolean;
  /** A large screen with a fine pointer: the full detail budget. */
  dense: boolean;
  /** Call once the first frame has drawn, so the scene can fade in. */
  onReady: () => void;
};
