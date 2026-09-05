function InsightGroup({ title, note, items }) {
  if (!items.length) return null;
  return (
    <div style={{ marginBottom: 28 }}>
      <h2 className="section-title">{title}</h2>
      <p className="section-note">{note}</p>
      <div>
        {items.map((item, i) => (
          <div className="insight-row" key={i}>
            <div className={`insight-marker ${item.severity}`} />
            <div>
              <p className="insight-title">{item.title}</p>
              <p className="insight-body">{item.explanation}</p>
            </div>
          </div>
        ))}
      </div>
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
