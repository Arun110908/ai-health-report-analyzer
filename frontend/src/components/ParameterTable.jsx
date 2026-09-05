const STATUS_LABEL = {
  normal: "normal",
  low: "low",
  high: "high",
  critical_low: "critical low",
  critical_high: "critical high",
  unknown: "n/a",
};

export default function ParameterTable({ parameters }) {
  return (
    <section>
      <h2 className="section-title">Blood parameters</h2>
      <p className="section-note">{parameters.length} parameters read from the report</p>
      <table className="param-table">
        <thead>
          <tr>
            <th style={{ width: "34%" }}>Parameter</th>
            <th style={{ width: "20%" }}>Value</th>
            <th style={{ width: "26%" }}>Reference range</th>
            <th style={{ width: "20%" }}>Status</th>
          </tr>
        </thead>
        <tbody>
          {parameters.map((p, i) => (
            <tr key={i}>
              <td className="param-name">{p.name}</td>
              <td className="param-value">
                {p.value ?? "—"} {p.unit || ""}
              </td>
              <td className="param-value" style={{ color: "var(--ink-soft)" }}>
                {p.reference_range || "—"}
              </td>
              <td>
                <span className={`status-pill status-${p.status}`}>
                  {STATUS_LABEL[p.status] || p.status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
