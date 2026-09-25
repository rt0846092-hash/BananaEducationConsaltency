const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

// Kept word-for-word in i18n.jsx so it can be shown in Nepali. The page fills
// in {phone} from the office config.
export const BUSY_MESSAGE =
  "Lots of people are using this network right now. Please call us on {phone} and we'll take your details.";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });

  if (res.status === 429) {
    // Many students can share one network at a fair or cyber cafe. Give them a
    // way through instead of DRF's "Expected available in 3600 seconds".
    throw new Error(BUSY_MESSAGE);
  }

  if (!res.ok) {
    let detail = "Something went wrong. Please try again.";
    try {
      const body = await res.json();
      // DRF returns { field: ["message"] }. Show the first real message
      // rather than a generic failure, so the person knows what to fix.
      const first = Object.values(body)[0];
      detail = Array.isArray(first) ? first[0] : body.detail || detail;
    } catch {
      /* response had no JSON body */
    }
    throw new Error(detail);
  }
  return res.status === 204 ? null : res.json();
}

export const api = {
  countries: () => request("/countries/"),
  country: (slug) => request(`/countries/${slug}/`),
  batches: () => request("/batches/"),
  counsellors: () => request("/counsellors/"),
  startIntake: (data) =>
    request("/leads/intake/", { method: "POST", body: JSON.stringify(data) }),
  // Step two carries the signed token from step one, never a database ID.
  finishIntake: (token, data) =>
    request("/leads/intake/details/", {
      method: "PATCH",
      body: JSON.stringify({ ...data, token }),
    }),
};
