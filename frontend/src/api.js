// Relative URLs: Vite proxies these to the FastAPI server in development.
export async function post(path, body) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
    throw new Error(detail || `Request failed (${res.status})`);
  }
  return data;
}

export async function get(path) {
  const res = await fetch(path);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
    throw new Error(detail || `Request failed (${res.status})`);
  }
  return data;
}

export const startIndex = (source) => post("/repos", { source });   // -> { job_id }
export const getJob = (jobId) => get(`/jobs/${jobId}`);
export const askRepo = (repoId, question) => post(`/repos/${repoId}/ask`, { question });
