"use client";

import { useEffect } from "react";

const STORAGE_KEY = "aether-atmosphere";
const ATMOSPHERES = ["forest", "lake", "dusk", "ocean", "desert"];

export function AtmosphereInit() {
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved && ATMOSPHERES.includes(saved) && saved !== "forest") {
      document.documentElement.classList.add(`atmosphere-${saved}`);
    }
  }, []);
  return null;
}
