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
 */
export function AtmosphereInit() {
  useEffect(() => {
    const saved = safeGet(STORAGE_KEY) as Atmosphere | null;
    if (!saved || saved === "forest") return;
    if (!ATMOSPHERES.includes(saved)) return;
    document.documentElement.classList.add(`atmosphere-${saved}`);
  }, []);
  return null;
}
