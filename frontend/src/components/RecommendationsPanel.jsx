const GROUPS = [
  { key: "diet_eat", label: "Foods to include", color: "var(--mint)" },
  { key: "diet_avoid", label: "Foods to limit", color: "var(--pulse)" },
  { key: "exercise", label: "Exercise", color: "var(--cyan)" },
  { key: "hydration", label: "Hydration", color: "var(--cyan-soft)" },
  { key: "sleep", label: "Sleep", color: "var(--violet)" },
  { key: "stress_management", label: "Stress management", color: "var(--violet-soft)" },
  { key: "lifestyle", label: "Lifestyle", color: "var(--amber)" },
];

export default function RecommendationsPanel({ recs }) {
  const groups = GROUPS.map((g) => ({ ...g, items: recs[g.key] })).filter((g) => g.items?.length);
  return (
    <section className="section-block">
      <h2 className="section-title">Personalized recommendations</h2>
      <p className="section-note">General wellness guidance based on this report &mdash; not a prescription</p>
      {groups.length ? (
        <div className="rec-grid">
          {groups.map((g) => (
            <div className="rec-card" key={g.key}>
              <div className="rec-head">
                <span className="rec-dot" style={{ background: g.color }} />
                <h4>{g.label}</h4>
              </div>
              <div className="rec-pills">
                {g.items.map((x, i) => (
                  <span className="rec-pill" key={i}>{x}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="empty-note">No specific recommendations for this report.</p>
      )}
    </section>
  );
}
