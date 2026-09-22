import { IconChevron } from "../icons.jsx";

export default function ExplanationsPanel({ explanations }) {
  const entries = Object.entries(explanations || {});
  if (!entries.length) return null;
  return (
    <section className="section-block">
      <h2 className="section-title">What each parameter means</h2>
      <p className="section-note">Plain-language explanations for every value in this report</p>
      <div className="explain-list">
        {entries.map(([name, text], i) => (
          <details className="explain-item" key={i} open={i === 0}>
            <summary>
              {name}
              <IconChevron />
            </summary>
            <p className="explain-body">{text}</p>
          </details>
        ))}
      </div>
    </section>
  );
}
