import { useRef, useState } from "react";
import { UploadIcon } from "../icons.jsx";

export default function UploadPanel({ onFile, onFiles, samples, onSample, loading }) {
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
  const analyzeFiles = (fileList) => {
    const files = Array.from(fileList);
    if (files.length > 1 && onFiles) onFiles(files, patientInfo());
    else if (files.length === 1) analyzeFile(files[0]);
  };
  const analyzeSample = (name) => onSample(name, patientInfo());

  const handleDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files?.length) analyzeFiles(e.dataTransfer.files);
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
        <p className="primary">Drop one or more blood reports here</p>
        <p className="secondary">PDF, JPG, PNG, or DOCX &mdash; select several files to analyze them together</p>
        <button className="btn-primary" onClick={() => inputRef.current?.click()} disabled={loading}>
          {loading ? "Analyzing\u2026" : "Choose file(s)"}
        </button>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf,.jpg,.jpeg,.png,.docx"
          style={{ display: "none" }}
          onChange={(e) => e.target.files?.length && analyzeFiles(e.target.files)}
        />
      </div>

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
