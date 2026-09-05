const BASE = import.meta.env.VITE_API_BASE || "";

export async function getStatus() {
  const res = await fetch(`${BASE}/api/status`);
  if (!res.ok) throw new Error("Failed to reach backend");
  return res.json();
}

export async function listSamples() {
  const res = await fetch(`${BASE}/api/sample-reports`);
  if (!res.ok) throw new Error("Failed to list sample reports");
  const data = await res.json();
  return data.samples || [];
}

export async function analyzeFile(file, patientInfo) {
  const form = new FormData();
  form.append("file", file);
  if (patientInfo) form.append("patient_info", JSON.stringify(patientInfo));
  const res = await fetch(`${BASE}/api/analyze`, { method: "POST", body: form });
  return res.json();
}

export async function analyzeSample(name) {
  const res = await fetch(`${BASE}/api/analyze-sample/${encodeURIComponent(name)}`, {
    method: "POST",
  });
  return res.json();
}
