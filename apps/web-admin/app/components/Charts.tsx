export function TrafficLine() {
  const points = "0,170 70,150 150,158 240,102 320,118 420,64 520,86 620,42";
  return (
    <div className="line-chart">
      <svg viewBox="0 0 640 220" role="img" aria-label="24h 流量曲线">
        <path d={`M ${points} L 620,220 L 0,220 Z`} fill="var(--accent-500)" opacity="0.04" />
        <polyline points={points} fill="none" stroke="var(--accent-500)" strokeWidth="1.25" />
        <circle cx="620" cy="42" r="4" fill="var(--gold)" />
      </svg>
    </div>
  );
}

export function WaveTrack({ variant = "user" }: { variant?: "user" | "tts" }) {
  const heights = variant === "user" ? [18, 42, 28, 54, 32, 62, 24, 48, 36, 58, 22, 40] : [22, 32, 44, 34, 52, 30, 46, 60, 38, 50, 26, 34];
  return (
    <div className="track">
      <div className="wave">
        {heights.map((height, index) => (
          <span style={{ height }} key={index} />
        ))}
      </div>
    </div>
  );
}

export function EventTrack() {
  return (
    <div className="track">
      <span className="event-dot" style={{ left: "18%" }} />
      <span className="event-dot" style={{ left: "42%" }} />
      <span className="event-dot" style={{ left: "58%" }} />
      <span className="event-dot" style={{ left: "74%" }} />
      <span className="cursor-line" />
    </div>
  );
}

