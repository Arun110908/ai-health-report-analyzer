import { useRef, useState } from "react";

export default function UploadPanel({ onFile, samples, onSample, loading }) {
  const inputRef = useRef(null);
  const [dragActive, setDragActive] = useState(false);

  const handleDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files?.[0];
    if (file) onFile(file);
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
        <p className="primary">Drop a blood report here</p>
        <p className="secondary">PDF, JPG, PNG, or DOCX &mdash; scanned reports are OCR'd automatically</p>
        <button className="btn" onClick={() => inputRef.current?.click()} disabled={loading}>
          {loading ? "Analyzing…" : "Choose a file"}
        </button>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.jpg,.jpeg,.png,.docx"
          style={{ display: "none" }}
          onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])}
        />
      </div>

      {samples?.length > 0 && (
        <>
          <p className="section-note" style={{ marginTop: 22 }}>
            Or try one of the bundled synthetic sample reports
          </p>
          <div className="sample-list">
            {samples.slice(0, 8).map((s) => (
              <button key={s} className="sample-chip" onClick={() => onSample(s)} disabled={loading}>
                {s}
              </button>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
