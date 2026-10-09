import { Component, type ReactNode } from "react";

/** If WebGL fails in any way, drop the canvas and leave the static poster: the hero never shows an error. */
export class SceneBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() { return this.state.failed ? null : this.props.children; }
}
