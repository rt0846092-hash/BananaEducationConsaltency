/**
 * Login state for the staff area.
 *
 * The token lives in localStorage so a counsellor stays logged in across page
 * refreshes — they work in this all day and being thrown out on every reload
 * would make it unusable. The trade-off is that localStorage is readable by
 * any script on the page, so a cross-site scripting bug would leak the token.
 * The safer production pattern is an httpOnly cookie the browser sends
 * automatically and JavaScript cannot read. Worth moving to before real
 * student data goes in.
 */

const KEY = "banana.token";

export const getToken = () => localStorage.getItem(KEY);
export const setToken = (t) => localStorage.setItem(KEY, t);
export const clearToken = () => localStorage.removeItem(KEY);

const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

export async function authFetch(path, options = {}) {
  const token = getToken();
  // File uploads send FormData; the browser must set that Content-Type itself.
  const isForm = options.body instanceof FormData;
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      ...(isForm ? {} : { "Content-Type": "application/json" }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });

  // Tokens expire after eight hours. Rather than showing a confusing error,
  // drop the dead token and let the router send them back to the login page.
  if (res.status === 401) {
    clearToken();
    throw new Error("SESSION_EXPIRED");
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    if (res.status === 403 && body.detail === "Set your own password before continuing.") {
      throw new Error("PASSWORD_CHANGE_REQUIRED");
    }
    const first = Object.values(body)[0];
    const err = new Error(
      body.detail || (Array.isArray(first) ? first[0] : null) || "Something went wrong."
    );
    // Callers sometimes need more than the message, e.g. the id of the
    // existing student when adding a duplicate returns 409.
    err.status = res.status;
    err.body = body;
    throw err;
  }
  return res.status === 204 ? null : res.json();
}

/** Downloads that need the sign-in header can't be plain links. */
export async function authDownload(path, fallbackName) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { Authorization: `Bearer ${getToken()}` },
  });
  if (res.status === 401) {
    clearToken();
    throw new Error("SESSION_EXPIRED");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "Download failed.");
  }
  const disposition = res.headers.get("Content-Disposition") || "";
  const match = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(disposition);
  const name = match ? decodeURIComponent(match[1]) : fallbackName;
  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export const staffApi = {
  login: async (username, password) => {
    const res = await fetch(`${BASE}/auth/login/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    // A locked-out owner who is told "wrong password" keeps guessing, which
    // only extends the lockout. Say what actually happened.
    if (res.status === 429) {
      throw new Error("Too many sign-in attempts from this network. Wait an hour and try again.");
    }
    if (!res.ok) throw new Error("That username and password don't match.");
    const { access } = await res.json();
    setToken(access);
    return access;
  },
  me: () => authFetch("/me/"),
  changePassword: (data) =>
    authFetch("/auth/password/", { method: "POST", body: JSON.stringify(data) }),
  leads: (query = "") => authFetch(`/leads/${query}`),
  addLead: (data) => authFetch("/leads/", { method: "POST", body: JSON.stringify(data) }),
  lead: (id) => authFetch(`/leads/${id}/`),
  updateLead: (id, data) =>
    authFetch(`/leads/${id}/`, { method: "PATCH", body: JSON.stringify(data) }),
  addNote: (id, data) =>
    authFetch(`/leads/${id}/notes/`, { method: "POST", body: JSON.stringify(data) }),
  dashboard: () => authFetch("/dashboard/"),
  counsellors: () => authFetch("/counsellors/"),
  countries: () => authFetch("/countries/"),
  universities: () => authFetch("/universities/"),

  addApplication: (leadId, data) =>
    authFetch(`/leads/${leadId}/applications/`, { method: "POST", body: JSON.stringify(data) }),
  updateApplication: (id, data) =>
    authFetch(`/applications/${id}/`, { method: "PATCH", body: JSON.stringify(data) }),

  uploadDocument: (leadId, formData) =>
    authFetch(`/leads/${leadId}/documents/`, { method: "POST", body: formData }),
  updateDocument: (id, data) =>
    authFetch(`/documents/${id}/`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteDocument: (id) => authFetch(`/documents/${id}/`, { method: "DELETE" }),
  downloadDocument: (doc) => authDownload(`/documents/${doc.id}/download/`, doc.original_name),

  // Owner only. The server returns 403 for anyone else, so these are safe to
  // reference even from a counsellor's session.
  team: () => authFetch("/team/"),
  handover: (data) =>
    authFetch("/team/handover/", { method: "POST", body: JSON.stringify(data) }),
  reports: (query = "") => authFetch(`/reports/${query}`),
  exportCsv: (query = "") => authDownload(`/leads/export/${query}`, "students.csv"),
};