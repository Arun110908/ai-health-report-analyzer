export default function ExplanationsPanel({ explanations }) {
  const entries = Object.entries(explanations || {});
  if (!entries.length) return null;
  return (
    <section>
      <h2 className="section-title">What each parameter means</h2>
      <p className="section-note">Plain-language explanations for every value in this report</p>
      <div className="explain-list">
        {entries.map(([name, text], i) => (
          <p className="explain-item" key={i}>
            <span className="term">{name}.</span> {text}
          </p>
        ))}
      </div>
    </section>
  );
}
