export default function HealthScoreHero({ report }) {
  const score = report.overall_health_score;
  return (
    <section>
      <p className="section-note" style={{ marginBottom: 0 }}>Overall health score</p>
      <div className="score-block">
        <span className="score-number">
          {score}
          <span className="score-max">/100</span>
        </span>
      </div>
      <div className="score-scale">
        <div className="score-marker" style={{ left: `calc(${score}% - 1px)` }} />
      </div>
      <div className="score-scale-labels">
        <span>0 &mdash; needs attention</span>
        <span>50</span>
        <span>100 &mdash; healthy range</span>
      </div>
      <p className="summary-text">{report.summary}</p>
    </section>
  );
}
