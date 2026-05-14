"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export function IntroScreen({ onComplete }: { onComplete: () => void }) {
  // 0=null(hidden), 1=dark screen(no shows), 2=glow, 3=particle, 4=title, 5=subtitle+deco, 10=exit
  const [step, setStep] = useState(0);
  const completedRef = useRef(false);
  const titleRef = useRef<HTMLDivElement>(null);

  const startExit = useCallback(() => {
    if (completedRef.current) return;
    completedRef.current = true;
    setStep(10);

    // Fly title to masthead — transform only, no opacity change.
    // Parent .intro-screen handles opacity via CSS fade, so adding
    // opacity here would compound them and cause premature disappearance.
    try {
      const fromEl = titleRef.current;
      const toEl = document.querySelector<HTMLElement>(".home-masthead-title");
      if (fromEl && toEl) {
        const fromRect = fromEl.getBoundingClientRect();
        const toRect = toEl.getBoundingClientRect();
        const scaleX = fromRect.width > 0 ? toRect.width / fromRect.width : 1;
        const scaleY = fromRect.height > 0 ? toRect.height / fromRect.height : 1;
        fromEl.animate(
          [
            { transform: "translate(0, 0) scale(1)", offset: 0 },
            {
              transform: `translate(${toRect.left - fromRect.left}px, ${toRect.top - fromRect.top}px) scale(${scaleX}, ${scaleY})`,
              offset: 1,
            },
          ],
          { duration: 700, easing: "cubic-bezier(0.76, 0, 0.24, 1)", fill: "forwards" }
        );
      }
    } catch {
      // WAAPI failure must not block onComplete
    }

    setTimeout(onComplete, 950);
  }, [onComplete]);

  useEffect(() => {
    if (
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ) {
      completedRef.current = true;
      onComplete();
      return;
    }

    // Step 0 keeps the component unmounted (null) so the map can start loading.
    // Step 1 mounts the dark overlay WITHOUT any .show classes so that when
    // .show is added in subsequent steps, CSS transitions fire on an already-
    // mounted element rather than on a freshly-inserted one (which skips them).
    const timers = [
      setTimeout(() => setStep(1), 60),    // mount dark overlay
      setTimeout(() => setStep(2), 140),   // glow expands
      setTimeout(() => setStep(3), 400),   // particle appears
      setTimeout(() => setStep(4), 800),   // title fades in
      setTimeout(() => setStep(5), 1300),  // subtitle + deco lines
      setTimeout(startExit, 5200),         // auto-advance
    ];
    return () => timers.forEach(clearTimeout);
  }, [onComplete, startExit]);

  if (step === 0) return null;

  const exiting = step === 10;

  return (
    <div
      className={`intro-screen${exiting ? " intro-done" : ""}`}
      aria-hidden="true"
      onClick={startExit}
    >
      <div className="intro-grain" />
      <div className={`intro-glow${step >= 2 ? " show" : ""}${exiting ? " fade" : ""}`} />

      <div className="intro-center">
        <div className={`intro-particle${step >= 3 ? " show" : ""}${exiting ? " fade" : ""}`} />

        <div
          ref={titleRef}
          className={`intro-title${step >= 4 ? " show" : ""}${exiting ? " flying" : ""}`}
        >
          <div className="intro-title-main">
            <span>坊巷</span>
            <span>知行</span>
          </div>
        </div>

        <p className={`intro-subtitle${step >= 5 ? " show" : ""}${exiting ? " out" : ""}`}>
          <span>三坊七巷</span>
          <span>·</span>
          <span>AI 智能导览</span>
        </p>

        <div className={`intro-deco-lines${step >= 5 ? " show" : ""}${exiting ? " out" : ""}`}>
          <span className="intro-deco-line left" />
          <span className="intro-deco-dot" />
          <span className="intro-deco-line right" />
        </div>
      </div>

      <p className="intro-skip-hint">轻触跳过</p>
    </div>
  );
}
