const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function req(path, opts) {
  let r;
  try {
    r = await fetch(BASE + path, opts);
  } catch {
    throw new Error("Cannot reach the API. Is the backend running on " + BASE + "?");
  }
  if (!r.ok) {
    let msg = r.statusText;
    try { msg = (await r.json()).detail || msg; } catch {}
    throw new Error(msg);
  }
  return r.json();
}

const post = (path, body) =>
  req(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });

export const api = {
  stats: () => req("/stats"),
  list: (status) => req("/documents" + (status ? `?status=${status}` : "")),
  get: (id) => req(`/documents/${id}`),
  upload: (file) => {
    const fd = new FormData();
    fd.append("file", file);
    return req("/documents/upload", { method: "POST", body: fd });
  },
  approve: (id, note) => post(`/documents/${id}/approve`, { note }),
  reject: (id, note) => post(`/documents/${id}/reject`, { note }),
  reprocess: (id) => post(`/documents/${id}/reprocess`),
  fileUrl: (id) => `${BASE}/documents/${id}/file`,
};
