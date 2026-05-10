"use client";

import { useEffect } from "react";

import type { Atmosphere } from "./demo-data";

const STORAGE_KEY = "aether-atmosphere";
const ATMOSPHERES: readonly Atmosphere[] = [
  "forest",
  "lake",
  "dusk",
  "ocean",
  "desert"
];

function safeGet(key: string): string | null {
  if (typeof window !== "object") return null;
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

/**
 * Applies the user-selected atmosphere class on mount so that tourist and
 * admin apps share the same "scenic skin". The default (forest) needs no
 * class because the base stylesheet already targets it.
 *
 * Also removes any stale atmosphere-* classes before applying the new one,
 * so that changing the value via devtools / another tab doesn't leave two
 * skins layered on the root element.
 */
export function AtmosphereInit() {
  useEffect(() => {
    const root = document.documentElement;
    // Clean any stale atmosphere-* class that might already be on <html>.
    for (const id of ATMOSPHERES) {
      root.classList.remove(`atmosphere-${id}`);
    }
    const saved = safeGet(STORAGE_KEY) as Atmosphere | null;
    if (!saved || saved === "forest") return;
    if (!ATMOSPHERES.includes(saved)) return;
    root.classList.add(`atmosphere-${saved}`);
  }, []);
  return null;
}
