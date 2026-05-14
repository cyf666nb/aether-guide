"use client";

import { useCallback, useEffect, useState } from "react";
import { getColorMode, setColorMode, type ColorMode } from "./atmosphere-init";

/**
 * An elegant sun/moon toggle that persists the user's color-mode preference.
 * Mounts reading from localStorage, then toggles in-place.
 */
export function ThemeToggle({ className = "" }: { className?: string }) {
  const [mode, setMode] = useState<ColorMode>("dark");

  useEffect(() => {
    setMode(getColorMode());
  }, []);

  const toggle = useCallback(() => {
    setMode((prev) => {
      const next = prev === "dark" ? "light" : "dark";
      setColorMode(next);
      return next;
    });
  }, []);

  const isLight = mode === "light";

  return (
    <button
      type="button"
      onClick={toggle}
      className={`theme-toggle ${className}`}
      aria-label={isLight ? "切换深色模式" : "切换浅色模式"}
      title={isLight ? "深色模式" : "浅色模式"}
    >
      <span className="theme-toggle-track">
        {/* Sun rays (visible in light mode) */}
        <svg
          className="theme-toggle-sun"
          viewBox="0 0 20 20"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.4"
          strokeLinecap="round"
        >
          <circle cx="10" cy="10" r="3.5" />
          <line x1="10" y1="2" x2="10" y2="4" />
          <line x1="10" y1="16" x2="10" y2="18" />
          <line x1="2" y1="10" x2="4" y2="10" />
          <line x1="16" y1="10" x2="18" y2="10" />
          <line x1="4.3" y1="4.3" x2="5.7" y2="5.7" />
          <line x1="14.3" y1="14.3" x2="15.7" y2="15.7" />
          <line x1="4.3" y1="15.7" x2="5.7" y2="14.3" />
          <line x1="14.3" y1="5.7" x2="15.7" y2="4.3" />
        </svg>
        {/* Moon crescent (visible in dark mode) */}
        <svg
          className="theme-toggle-moon"
          viewBox="0 0 20 20"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.4"
          strokeLinecap="round"
        >
          <path d="M15.5 10.5a5.5 5.5 0 0 1-7-7 5.5 5.5 0 1 0 7 7Z" />
        </svg>
        {/* Sliding dot */}
        <span className="theme-toggle-knob" />
      </span>
    </button>
  );
}
