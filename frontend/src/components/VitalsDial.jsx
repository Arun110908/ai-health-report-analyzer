import { useEffect, useRef, useState } from "react";

// Three-quarter circle gauge (270deg), drawn with the pathLength trick so the
// dasharray math stays in "percent of arc" regardless of the true radius.
const ARC_FRACTION = 270 / 360;
const ROTATE = 135; // rotates the open gap to the bottom of the circle

function bandFor(score) {
  if (score >= 70) return { color: "var(--mint)", soft: "var(--mint-soft)", bg: "rgba(51, 230, 184, 0.14)", label: "Healthy range" };
  if (score >= 40) return { color: "var(--amber)", soft: "var(--amber-soft)", bg: "rgba(255, 182, 72, 0.14)", label: "Needs attention" };
  return { color: "var(--pulse)", soft: "var(--pulse-soft)", bg: "rgba(255, 93, 124, 0.16)", label: "Review with a doctor" };
}

export default function VitalsDial({ score }) {
  const [drawn, setDrawn] = useState(0);
  const raf = useRef(null);

  useEffect(() => {
    setDrawn(0);
    raf.current = requestAnimationFrame(() => requestAnimationFrame(() => setDrawn(score)));
    return () => cancelAnimationFrame(raf.current);
  }, [score]);

  const band = bandFor(score);
  const trackDash = `${ARC_FRACTION * 100} 100`;
  const valueDash = `${(drawn / 100) * ARC_FRACTION * 100} 100`;

  return (
    <div className="dial-card">
      <svg className="dial-svg" viewBox="0 0 200 200">
        <circle
          cx="100" cy="100" r="82" pathLength="100" fill="none"
          stroke="var(--line-soft)" strokeWidth="14" strokeLinecap="round"
          strokeDasharray={trackDash}
          transform={`rotate(${ROTATE} 100 100)`}
        />
        <circle
          cx="100" cy="100" r="82" pathLength="100" fill="none"
          stroke={band.color} strokeWidth="14" strokeLinecap="round"
          strokeDasharray={valueDash}
          transform={`rotate(${ROTATE} 100 100)`}
          style={{ transition: "stroke-dasharray 1.1s cubic-bezier(.22,1,.36,1)" }}
        />
        <text x="100" y="96" textAnchor="middle" className="dial-num" fontSize="42">
          {Math.round(drawn)}
        </text>
        <text x="100" y="118" textAnchor="middle" className="dial-max">out of 100</text>
      </svg>
      <p className="dial-label">Overall health score</p>
      <span className="dial-band" style={{ color: band.soft, background: band.bg }}>{band.label}</span>
    </div>
  );
}
