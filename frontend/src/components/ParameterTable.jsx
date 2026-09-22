const STATUS_LABEL = {
  normal: "normal",
  low: "low",
  high: "high",
  critical_low: "critical low",
  critical_high: "critical high",
  unknown: "n/a",
};

const DOT_COLOR = {
  normal: "var(--mint)",
  low: "var(--amber)",
  high: "var(--amber)",
  critical_low: "var(--pulse)",
  critical_high: "var(--pulse)",
  unknown: "var(--muted-dim)",
};

// Reads "13.0-17.0", "<200" or ">40" and returns a 0-1 position for the dot,
// clamped a little outside the band so an out-of-range value is still visible.
function parseRange(text) {
  if (!text) return null;
  let m = text.match(/^([\d.]+)\s*-\s*([\d.]+)$/);
  if (m) return { lo: parseFloat(m[1]), hi: parseFloat(m[2]) };
  m = text.match(/^<\s*([\d.]+)$/);
  if (m) return { lo: 0, hi: parseFloat(m[1]) };
  m = text.match(/^>\s*([\d.]+)$/);
  if (m) return { lo: parseFloat(m[1]), hi: parseFloat(m[1]) * 2 };
  return null;
}

function RangeBar({ value, rangeText, status }) {
  const r = parseRange(rangeText);
  if (!r || value == null || r.hi <= r.lo) {
    return <div className="range-track" />;
  }
  const pos = Math.min(Math.max((value - r.lo) / (r.hi - r.lo), -0.25), 1.25);
  return (
    <div className="range-track">
      <div className="band" style={{ left: "16.7%", right: "16.7%" }} />
      <div className="dot" style={{ left: `${16.7 + pos * 66.6}%`, background: DOT_COLOR[status] || "var(--cyan)" }} />
    </div>
  );
}

export default function ParameterTable({ parameters }) {
  return (
    <section className="section-block">
      <h2 className="section-title">Blood parameters</h2>
      <p className="section-note">{parameters.length} parameters read from the report</p>
      <div className="trace-list">
        {parameters.map((p, i) => (
          <div className={`trace-row s-${p.status}`} key={i}>
            <div className="trace-name">{p.name}</div>
            <div className="trace-value">
              {p.value ?? "\u2014"}
              {p.unit ? <span className="unit">{p.unit}</span> : null}
            </div>
            <div className="trace-range">
              <span className="range-text">{p.reference_range || "range n/a"}</span>
              <RangeBar value={p.value} rangeText={p.reference_range} status={p.status} />
            </div>
            <span className={`status-chip s-${p.status}`}>{STATUS_LABEL[p.status] || p.status}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
