function InsightGroup({ title, note, items }) {
  return (
    <div className="section-block">
      <h2 className="section-title">{title}</h2>
      <p className="section-note">{note}</p>
      {items.length ? (
        <div className="insight-grid">
          {items.map((item, i) => (
            <div className={`insight-card sev-${item.severity}`} key={i}>
              <p className="insight-title">{item.title}</p>
              <p className="insight-body">{item.explanation}</p>
            </div>
          ))}
        </div>
      ) : (
        <p className="empty-note">Nothing flagged here for this report.</p>
      )}
    </div>
  );
}

export default function InsightsPanel({ report }) {
  return (
    <>
      <InsightGroup
        title="Possible deficiencies"
        note="Flagged from parameters below the healthy reference range"
        items={report.deficiencies}
      />
      <InsightGroup
        title="Other health risks to watch"
        note="Abnormal values that may signal a broader risk"
        items={report.health_risks}
      />
    </>
  );
}
