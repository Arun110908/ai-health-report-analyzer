const BASE = import.meta.env.VITE_API_BASE || "";

async function readError(res) {
  // Surface the REAL failure reason instead of a generic "backend
  // unreachable" message -- e.g. a Render free-tier cold start returns a
  // plain-text/HTML 502 that isn't JSON, which used to throw an opaque
  // parse error here and get swallowed into a useless message upstream.
  let detail = "";
  try {
    const body = await res.clone().json();
    detail = body.detail || JSON.stringify(body);
  } catch {
    try { detail = (await res.text()).slice(0, 200); } catch { /* ignore */ }
  }
  const hint = res.status === 502 || res.status === 503
    ? " The server may still be waking up (free-tier cold start) -- try again in ~30 seconds."
    : "";
  throw new Error(`Server responded ${res.status} ${res.statusText}.${detail ? " " + detail : ""}${hint}`);
}

export async function getStatus() {
  const res = await fetch(`${BASE}/api/status`);
  if (!res.ok) await readError(res);
  return res.json();
}

export async function listSamples() {
  const res = await fetch(`${BASE}/api/sample-reports`);
  if (!res.ok) await readError(res);
  const data = await res.json();
  return data.samples || [];
}

export async function analyzeFile(file, patientInfo) {
  const form = new FormData();
  form.append("file", file);
  if (patientInfo) form.append("patient_info", JSON.stringify(patientInfo));
  const res = await fetch(`${BASE}/api/analyze`, { method: "POST", body: form });
  if (!res.ok) await readError(res);
  return res.json();
}

export async function analyzeSample(name, patientInfo) {
  const form = new FormData();
  if (patientInfo) form.append("patient_info", JSON.stringify(patientInfo));
  const res = await fetch(`${BASE}/api/analyze-sample/${encodeURIComponent(name)}`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) await readError(res);
  return res.json();
}

export async function analyzeBatch(files, patientInfo) {
  const form = new FormData();
  for (const f of files) form.append("files", f);
  if (patientInfo) form.append("patient_info", JSON.stringify(patientInfo));
  const res = await fetch(`${BASE}/api/analyze-batch`, { method: "POST", body: form });
  if (!res.ok) await readError(res);
  return res.json();
}
