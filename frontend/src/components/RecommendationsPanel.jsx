function Group({ label, items }) {
  if (!items || !items.length) return null;
  return (
    <div className="rec-group">
      <h4>{label}</h4>
      <ul>
        {items.map((x, i) => (
          <li key={i}>{x}</li>
        ))}
      </ul>
    </div>
  );
}

export default function RecommendationsPanel({ recs }) {
  return (
    <section>
      <h2 className="section-title">Personalized recommendations</h2>
      <p className="section-note">General wellness guidance based on this report &mdash; not a prescription</p>
      <div className="rec-grid">
        <Group label="Foods to include" items={recs.diet_eat} />
        <Group label="Foods to limit" items={recs.diet_avoid} />
        <Group label="Exercise" items={recs.exercise} />
        <Group label="Hydration" items={recs.hydration} />
        <Group label="Sleep" items={recs.sleep} />
        <Group label="Stress management" items={recs.stress_management} />
        <Group label="Lifestyle" items={recs.lifestyle} />
      </div>
    </section>
  );
}
