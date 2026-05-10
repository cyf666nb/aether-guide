import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement> & {
  title?: string;
};

const strokeProps = {
  fill: "none",
  stroke: "currentColor",
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  strokeWidth: 1.25,
};

export function AetherLogo({ title = "Aether Guide", ...props }: IconProps) {
  return (
    <svg viewBox="0 0 48 48" aria-label={title} role="img" {...props}>
      <path {...strokeProps} d="M8 28c7-13 20-20 32-18-5 10-14 17-27 22" />
      <path {...strokeProps} d="M13 32c8 5 18 6 28 2-6 7-17 10-28 6" />
      <path {...strokeProps} d="M23 13c2 9 1 18-4 27" />
      <circle cx="31" cy="20" r="2.5" fill="currentColor" />
    </svg>
  );
}

export function HumanBadge({ title = "Digital human", ...props }: IconProps) {
  return (
    <svg viewBox="0 0 48 48" aria-label={title} role="img" {...props}>
      <path {...strokeProps} d="M14 35c2-7 6-10 10-10s8 3 10 10" />
      <circle {...strokeProps} cx="24" cy="17" r="7" />
      <path {...strokeProps} d="M10 24c0-11 7-18 14-18s14 7 14 18" />
      <path {...strokeProps} d="M8 34c8 8 24 8 32 0" />
    </svg>
  );
}

export function KnowledgeMark({ title = "Knowledge base", ...props }: IconProps) {
  return (
    <svg viewBox="0 0 48 48" aria-label={title} role="img" {...props}>
      <path {...strokeProps} d="M11 10h17c5 0 9 4 9 9v19H20c-5 0-9-4-9-9V10Z" />
      <path {...strokeProps} d="M18 18h14M18 25h14M18 32h8" />
      <path {...strokeProps} d="M37 19c-5 0-9-4-9-9" />
    </svg>
  );
}

export function ThinkingGlyph({ title = "AI thinking", ...props }: IconProps) {
  return (
    <svg viewBox="0 0 48 48" aria-label={title} role="img" {...props}>
      <path {...strokeProps} d="M14 25c0-7 5-12 11-12 5 0 9 3 9 8 0 6-6 7-6 12" />
      <path {...strokeProps} d="M18 36h12M20 41h8" />
      <circle cx="18" cy="23" r="1.8" fill="currentColor" />
      <circle cx="25" cy="21" r="1.8" fill="currentColor" />
      <circle cx="32" cy="23" r="1.8" fill="currentColor" />
    </svg>
  );
}

export function CameraGlyph({ title = "Camera", ...props }: IconProps) {
  return (
    <svg viewBox="0 0 48 48" aria-label={title} role="img" {...props}>
      <path {...strokeProps} d="M36 14h-3l-2-4H17l-2 4h-3a3 3 0 0 0-3 3v14a3 3 0 0 0 3 3h24a3 3 0 0 0 3-3V17a3 3 0 0 0-3-3Z" />
      <circle {...strokeProps} cx="24" cy="25" r="6" />
      <circle cx="24" cy="25" r="2" fill="currentColor" />
    </svg>
  );
}

export function ScanGlyph({ title = "Scanning", ...props }: IconProps) {
  return (
    <svg viewBox="0 0 48 48" aria-label={title} role="img" {...props}>
      <path {...strokeProps} d="M13 8h-3a2 2 0 0 0-2 2v3M35 8h3a2 2 0 0 1 2 2v3" />
      <path {...strokeProps} d="M13 40h-3a2 2 0 0 1-2-2v-3M35 40h3a2 2 0 0 0 2-2v-3" />
      <path {...strokeProps} d="M12 24h24" />
      <path {...strokeProps} d="M18 17c4-3 8-3 12 0M18 31c4 3 8 3 12 0" />
    </svg>
  );
}

