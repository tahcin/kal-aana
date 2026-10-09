import { useEffect } from "react";

const BASE = "Kal Aana";

/** Sets the tab title for a page ("Kal Aana · Map"); pass nothing to leave the default. */
export function useTitle(title?: string | null) {
  useEffect(() => {
    document.title = title ? `${BASE} · ${title}` : BASE;
  }, [title]);
}
