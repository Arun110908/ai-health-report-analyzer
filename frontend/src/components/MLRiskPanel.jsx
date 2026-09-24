const statusTitle = {
  available: "Metabolic risk demo",
  insufficient_data: "Metabolic risk demo needs more context",
  model_not_trained: "Metabolic risk demo is not trained",
  unavailable: "Metabolic risk demo is unavailable",
};

function scoreClass(band) {
  if (band === "High") return "risk-high";
  if (band === "Moderate") return "risk-moderate";
  return "risk-low";
}

export default function MLRiskPanel({ prediction }) {
  if (!prediction) return null;

  const available = prediction.status === "available";
  const score = Number.isFinite(prediction.risk_score)
    ? Math.round(prediction.risk_score * 100)
    : null;

  return (
    <section className="ml-panel" aria-labelledby="ml-risk-heading">
      <div className="section-heading-row">
        <div>
          <p className="eyebrow">Optional academic model</p>
          <h2 id="ml-risk-heading">{statusTitle[prediction.status] || "Metabolic risk demo"}</h2>
        </div>
        {available && (
          <span className={`risk-band ${scoreClass(prediction.risk_band)}`}>
            {prediction.risk_band} estimate
          </span>
        )}
      </div>

      {available ? (
        <>
          <div className="risk-summary">
            <p className={`risk-score ${scoreClass(prediction.risk_band)}`}>{score}%</p>
            <div>
              <p className="risk-summary-title">Ensemble estimate</p>
              <p className="risk-message">{prediction.message}</p>
              {Number.isFinite(prediction.model_agreement) && (
                <p className="model-agreement">
                  Model agreement: {Math.round(prediction.model_agreement * 100)}%
                </p>
              )}
            </div>
          </div>

          {prediction.top_contributors?.length > 0 && (
            <div className="contributors">
              <h3>Largest LightGBM SHAP contributions</h3>
              <ul>
                {prediction.top_contributors.map((item) => (
                  <li key={item.feature}>
                    <span>{item.display_name}</span>
                    <span className={item.shap_contribution >= 0 ? "shap-positive" : "shap-negative"}>
                      {item.shap_contribution >= 0 ? "+" : ""}{item.shap_contribution.toFixed(3)}
                    </span>
                  </li>
                ))}
              </ul>
              <p className="shap-note">Positive values push the LightGBM estimate higher; negative values push it lower.</p>
            </div>
          )}
        </>
      ) : (
        <>
          <p className="risk-message">{prediction.message}</p>
          {prediction.missing_features?.length > 0 && (
            <p className="missing-features">
              Still needed: {prediction.missing_features.join(", ")}.
            </p>
          )}
        </>
      )}

      <p className="ml-disclaimer">{prediction.disclaimer}</p>
    </section>
  );
}
