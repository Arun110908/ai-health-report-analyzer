import { useEffect, useState } from "react";
import { getStatus, listSamples, analyzeFile, analyzeSample } from "./api";
import { BrandMark, EkgTrace, IconUpload, IconReport } from "./icons.jsx";
import UploadPanel from "./components/UploadPanel.jsx";
import VitalsDial from "./components/VitalsDial.jsx";
import AlertBanner from "./components/AlertBanner.jsx";
import ParameterTable from "./components/ParameterTable.jsx";
import InsightsPanel from "./components/InsightsPanel.jsx";
import RecommendationsPanel from "./components/RecommendationsPanel.jsx";
import ExplanationsPanel from "./components/ExplanationsPanel.jsx";
import MLRiskPanel from "./components/MLRiskPanel.jsx";

export default function App() {
  const [status, setStatus] = useState(null);
  const [samples, setSamples] = useState([]);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [view, setView] = useState("upload");

  useEffect(() => {
    getStatus().then(setStatus).catch(() => setStatus(null));
    listSamples().then(setSamples).catch(() => setSamples([]));
  }, []);

  const runAnalysis = async (promise) => {
    setLoading(true);
    setError(null);
    try {
      const data = await promise;
      if (data.success) {
        setReport(data.report);
        setView("report");
      } else {
        setError((data.errors && data.errors.join(" ")) || "Analysis failed.");
      }
    } catch (e) {
      setError("Could not reach the backend. Is the FastAPI server running?");
    } finally {
      setLoading(false);
    }
  };

  const Brand = ({ small }) => (
    <div className="brand-row">
      <BrandMark size={small ? 26 : 30} />
      <span className="brand-word">AXD</span>
    </div>
  );

  const Nav = ({ className, compact }) => (
    <>
      <button className={`${className} ${view === "upload" ? "active" : ""}`} onClick={() => setView("upload")}>
        <IconUpload />
        {compact ? "Upload" : "Upload report"}
      </button>
      <button
        className={`${className} ${view === "report" ? "active" : ""}`}
        onClick={() => report && setView("report")}
        disabled={!report}
      >
        <IconReport />
        Report
      </button>
    </>
  );

  return (
    <div className="shell">
      <aside className="rail">
        <Brand />
        <p className="brand-tagline">Turns a blood report into a plain-language health summary.</p>

        <nav className="rail-nav">
          <Nav className="nav-btn" />
        </nav>

        <div className="rail-status">
          <div className="rail-status-row">
            <span className={`status-dot ${status ? "" : "off"}`} />
            <span className="value">{status ? "Backend connected" : "Backend offline"}</span>
          </div>
          {status && (
            <>
              <div className="rail-status-row">
                <span className="label">engine</span>
                <span className="value">{status.pipeline_engine}</span>
              </div>
              <div className="rail-status-row">
                <span className="label">model</span>
                <span className="value">{status.llm_enabled ? "Claude API" : "rule-based"}</span>
              </div>
            </>
          )}
        </div>
      </aside>

      <header className="topbar">
        <Brand small />
        <span className={`status-dot ${status ? "" : "off"}`} />
      </header>

      <main className="main">
        {view === "upload" && (
          <>
            <h1 className="page-title">Understand your blood report</h1>
            <p className="page-lede">
              Upload a lab report and a four-agent pipeline extracts every parameter, compares it
              against WHO / NIH / Mayo Clinic reference ranges, and turns it into a plain-language
              health summary with personalized recommendations.
            </p>
            <UploadPanel
              onFile={(file, patientInfo) => runAnalysis(analyzeFile(file, patientInfo))}
              samples={samples}
              onSample={(name, patientInfo) => runAnalysis(analyzeSample(name, patientInfo))}
              loading={loading}
            />
            {loading && (
              <div className="loading-state">
                <div className="ekg-wrap">
                  <EkgTrace />
                </div>
                <div>
                  <p className="loading-text">Running the report through the four agents</p>
                  <p className="loading-sub">Reading, analyzing, and writing your summary&hellip;</p>
                </div>
              </div>
            )}
            {error && <div className="error-box">{error}</div>}
          </>
        )}

        {view === "report" && report && (
          <>
            <h1 className="page-title">Health summary</h1>
            <AlertBanner report={report} />
            <div className="hero-grid">
              <VitalsDial score={report.overall_health_score} />
              <div className="side-card">
                <p className="summary-text">{report.summary}</p>
              </div>
            </div>
            <ParameterTable parameters={report.parameters} />
            <InsightsPanel report={report} />
            <MLRiskPanel prediction={report.metabolic_risk} />
            <RecommendationsPanel recs={report.recommendations} />
            <ExplanationsPanel explanations={report.parameter_explanations} />
            <p className="disclaimer">
              This report is generated by an AI system for informational purposes only. It is not a
              medical diagnosis and does not replace advice from a qualified healthcare
              professional. Always consult your doctor about any abnormal results.
            </p>
          </>
        )}
      </main>

      <nav className="tabbar">
        <Nav className="tab-btn" compact />
      </nav>
    </div>
  );
}
