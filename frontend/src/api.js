/* Tiny fetch wrapper around the FastAPI backend. Token lives in localStorage. */

const TOKEN_KEY = "vcs_token";

function authHeaders(extra = {}) {
  const t = localStorage.getItem(TOKEN_KEY);
  return t ? { Authorization: `Bearer ${t}`, ...extra } : extra;
}

async function req(path, { method = "GET", body = null, form = false } = {}) {
  const headers = form ? authHeaders() : authHeaders({ "Content-Type": "application/json" });
  const res = await fetch(`/api${path}`, {
    method,
    headers,
    body: body == null ? undefined : form ? body : JSON.stringify(body),
  });
  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { detail: text };
  }
  if (!res.ok) {
    const msg = (data && data.detail) || `Request failed (${res.status})`;
    const err = new Error(Array.isArray(msg) ? msg.map((m) => m.msg).join("; ") : msg);
    err.status = res.status;
    throw err;
  }
  return data;
}

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t) => (t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY)),
};

export const api = {
  signup: (email, artist_name, password) =>
    req("/auth/signup", { method: "POST", body: { email, artist_name, password } }),
  login: (email, password) => req("/auth/login", { method: "POST", body: { email, password } }),
  me: () => req("/auth/me"),

  listVoiceprints: () => req("/voiceprints"),
  enrollVoiceprint: (label, file) => {
    const fd = new FormData();
    fd.append("label", label);
    fd.append("file", file);
    return req("/voiceprints", { method: "POST", body: fd, form: true });
  },
  deleteVoiceprint: (id) => req(`/voiceprints/${id}`, { method: "DELETE" }),

  runCheck: (file, voiceprintId) => {
    const fd = new FormData();
    fd.append("file", file);
    if (voiceprintId) fd.append("voiceprint_id", String(voiceprintId));
    return req("/checks", { method: "POST", body: fd, form: true });
  },
  listChecks: () => req("/checks"),
  sendFeedback: (id, verdict, note) =>
    req(`/checks/${id}/feedback`, { method: "POST", body: { verdict, note: note || null } }),

  async downloadEvidence(id) {
    const res = await fetch(`/api/checks/${id}/evidence`, { headers: authHeaders() });
    if (!res.ok) throw new Error(`Evidence download failed (${res.status})`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `voice-clone-shield-evidence-${String(id).padStart(6, "0")}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
  },
};
