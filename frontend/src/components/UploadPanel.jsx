import { useRef, useState } from "react";
import { UploadIcon } from "../icons.jsx";

export default function UploadPanel({ onFile, samples, onSample, loading, selectedFile }) {
  const inputRef = useRef(null);
  const [dragActive, setDragActive] = useState(false);
  const [showContext, setShowContext] = useState(false);
  const [context, setContext] = useState({
    age: "",
    bmi: "",
    systolic_bp: "",
    fasting_glucose: "",
    fasting_insulin: "",
    total_cholesterol: "",
    hba1c: "",
    post_meal_glucose: "",
  });

  const patientInfo = () => Object.fromEntries(
    Object.entries(context)
      .filter(([, value]) => value !== "")
      .map(([key, value]) => [key, Number(value)]),
  );

  const updateContext = (event) => {
    const { name, value } = event.target;
    setContext((current) => ({ ...current, [name]: value }));
  };

  const analyzeFile = (file) => onFile(file, patientInfo());
  const analyzeSample = (name) => onSample(name, patientInfo());

  const handleDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files?.[0];
    if (file) analyzeFile(file);
  };

  return (
    <section>
      <div
        className={`dropzone ${dragActive ? "drag-active" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
      >
        <UploadIcon />
        <p className="primary">Drop a blood report here</p>
        <p className="secondary">PDF, JPG, PNG, or DOCX &mdash; scanned reports are read automatically</p>
        <button className="btn-primary" onClick={() => inputRef.current?.click()} disabled={loading}>
          {loading ? "Analyzing\u2026" : "Choose a file"}
        </button>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.jpg,.jpeg,.png,.docx"
          style={{ display: "none" }}
          onChange={(e) => e.target.files?.[0] && analyzeFile(e.target.files[0])}
        />
      </div>

      {selectedFile && (
        <div className="selected-file" aria-live="polite">
          {selectedFile.previewUrl ? (
            <img src={selectedFile.previewUrl} alt={`Preview of ${selectedFile.name}`} />
          ) : (
            <div className="file-placeholder">REPORT</div>
          )}
          <div>
            <p className="selected-file-label">Selected report</p>
            <p className="selected-file-name">{selectedFile.name}</p>
          </div>
        </div>
      )}

      <div className="context-panel">
        <button
          type="button"
          className="context-toggle"
          onClick={() => setShowContext((visible) => !visible)}
          aria-expanded={showContext}
        >
          {showContext ? "Hide" : "Add"} optional context for the metabolic-risk demo
        </button>
        {showContext && (
          <>
            <p className="context-note">
              These eight values are optional, stay in this analysis request, and are used only for the LightGBM + KNN academic demo. Values parsed from the report take priority.
            </p>
            <div className="context-fields">
              <label>
                Age
                <input name="age" type="number" min="1" max="120" value={context.age} onChange={updateContext} />
              </label>
              <label>
                BMI (kg/m²)
                <input name="bmi" type="number" min="10" max="70" step="0.1" value={context.bmi} onChange={updateContext} />
              </label>
              <label>
                Systolic BP
                <input name="systolic_bp" type="number" min="60" max="250" value={context.systolic_bp} onChange={updateContext} />
              </label>
              <label>
                Fasting glucose
                <input name="fasting_glucose" type="number" min="40" max="500" value={context.fasting_glucose} onChange={updateContext} />
              </label>
              <label>
                Fasting insulin
                <input name="fasting_insulin" type="number" min="0" max="900" step="0.1" value={context.fasting_insulin} onChange={updateContext} />
              </label>
              <label>
                Total cholesterol
                <input name="total_cholesterol" type="number" min="80" max="500" value={context.total_cholesterol} onChange={updateContext} />
              </label>
              <label>
                HbA1c (%)
                <input name="hba1c" type="number" min="3" max="18" step="0.1" value={context.hba1c} onChange={updateContext} />
              </label>
              <label>
                Post-meal glucose
                <input name="post_meal_glucose" type="number" min="40" max="500" value={context.post_meal_glucose} onChange={updateContext} />
              </label>
            </div>
          </>
        )}
      </div>

      {samples?.length > 0 && (
        <>
          <p className="section-note samples-label">Or try one of the bundled synthetic sample reports</p>
          <div className="sample-list">
            {samples.slice(0, 8).map((s) => (
              <button key={s} className="sample-chip" onClick={() => analyzeSample(s)} disabled={loading}>
                {s}
              </button>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
