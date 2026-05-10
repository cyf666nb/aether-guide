"use client";

/**
 * Lightweight skeleton primitives.
 *
 * Why custom and not e.g. shadcn/ui? The tourist shell already has its own
 * "linjing" theme tokens; pulling in another design system would duplicate
 * variables. These components honor the same `--stone-*` / `--ink-*` palette.
 */

import type { CSSProperties, ReactNode } from "react";

type SkeletonProps = {
  width?: number | string;
  height?: number | string;
  radius?: number | string;
  className?: string;
  style?: CSSProperties;
  /** A11y label. Defaults to "正在加载". Pass "" to opt out. */
  label?: string;
};

const baseStyle: CSSProperties = {
  display: "inline-block",
  background:
    "linear-gradient(90deg, rgba(232, 228, 220, 0.06) 0%, rgba(232, 228, 220, 0.14) 50%, rgba(232, 228, 220, 0.06) 100%)",
  backgroundSize: "200% 100%",
  animation: "aether-skeleton-shimmer 1.4s ease-in-out infinite",
};

/** A single rectangular shimmer bar. */
export function Skeleton({
  width = "100%",
  height = 12,
  radius = 8,
  className,
  style,
  label = "正在加载",
}: SkeletonProps) {
  return (
    <span
      role={label ? "status" : undefined}
      aria-label={label || undefined}
      aria-live="polite"
      aria-busy="true"
      className={className}
      style={{
        ...baseStyle,
        width,
        height,
        borderRadius: radius,
        ...style,
      }}
    />
  );
}

/** A multi-line text skeleton (last line is shorter, like real text). */
export function SkeletonText({
  lines = 3,
  lineHeight = 12,
  gap = 8,
  className,
}: {
  lines?: number;
  lineHeight?: number;
  gap?: number;
  className?: string;
}) {
  const items = Array.from({ length: lines });
  return (
    <span
      role="status"
      aria-label="正在加载"
      aria-busy="true"
      className={className}
      style={{
        display: "flex",
        flexDirection: "column",
        gap,
        width: "100%",
      }}
    >
      {items.map((_, idx) => (
        <Skeleton
          key={idx}
          height={lineHeight}
          width={idx === items.length - 1 ? "62%" : "100%"}
          // Inner skeletons share the parent's status role.
          label=""
        />
      ))}
    </span>
  );
}

/** A landmark card skeleton — matches the shape of `<LandmarkCard />`. */
export function LandmarkCardSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div
      role="status"
      aria-label="景点列表加载中"
      aria-busy="true"
      style={{
        display: "grid",
        gap: 12,
      }}
    >
      {Array.from({ length: count }).map((_, idx) => (
        <div
          key={idx}
          style={{
            display: "flex",
            gap: 12,
            padding: 12,
            borderRadius: 16,
            background: "rgba(255, 255, 255, 0.03)",
            border: "1px solid rgba(255, 255, 255, 0.06)",
          }}
        >
          <Skeleton width={64} height={64} radius={12} label="" />
          <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 8 }}>
            <Skeleton height={14} width="40%" label="" />
            <SkeletonText lines={2} lineHeight={10} />
          </div>
        </div>
      ))}
    </div>
  );
}

/** Wrap content with a fade-in once loaded. */
export function FadeIn({ children }: { children: ReactNode }) {
  return (
    <span
      style={{
        animation: "aether-skeleton-fade-in 240ms ease-out both",
      }}
    >
      {children}
    </span>
  );
}
