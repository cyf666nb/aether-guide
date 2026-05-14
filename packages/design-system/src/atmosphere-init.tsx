"use client";

import { useEffect } from "react";

import type { Atmosphere } from "./demo-data";

const STORAGE_KEY = "aether-atmosphere";
const MODE_STORAGE_KEY = "aether-mode";
const ATMOSPHERES: readonly Atmosphere[] = [
  "forest",
  "lake",
  "dusk",
  "ocean",
  "desert"
];

export type ColorMode = "dark" | "light";

function safeGet(key: string): string | null {
  if (typeof window !== "object") return null;
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function safeSet(key: string, value: string): void {
  if (typeof window !== "object") return;
  try {
    window.localStorage.setItem(key, value);
  } catch {
    /* storage full or private mode */
  }
}

/** Returns the persisted color mode, defaulting to "dark". */
export function getColorMode(): ColorMode {
  const saved = safeGet(MODE_STORAGE_KEY);
  return saved === "light" ? "light" : "dark";
}

/** Persists and applies the given color mode to <html>. */
export function setColorMode(mode: ColorMode): void {
  const root = document.documentElement;
  root.setAttribute("data-mode", mode);
  safeSet(MODE_STORAGE_KEY, mode);
  // Update theme-color meta tag for mobile chrome
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) {
    meta.setAttribute("content", mode === "light" ? "#FAF7F0" : "#0B0E10");
  }
}

/** Toggles between dark and light, returning the new mode. */
export function toggleColorMode(): ColorMode {
  const next = getColorMode() === "dark" ? "light" : "dark";
  setColorMode(next);
  return next;
}

/**
 * Applies the user-selected atmosphere class on mount so that tourist and
 * admin apps share the same "scenic skin". The default (forest) needs no
 * class because the base stylesheet already targets it.
 *
 * Also removes any stale atmosphere-* classes before applying the new one,
 * so that changing the value via devtools / another tab doesn't leave two
 * skins layered on the root element.
 *
 * Restores persisted color mode (dark/light) from localStorage.
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

  useEffect(() => {
    setColorMode(getColorMode());
  }, []);

  return null;
}
