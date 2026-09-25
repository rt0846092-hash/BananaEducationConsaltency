/**
 * The site is English only. Students applying abroad need English for the
 * application, the test and the degree, so a Nepali version was removed.
 *
 * t() is kept so pages can fill in values ("{n} weeks") in one place, and so a
 * translation could be added back later without touching every page.
 */

export function LangProvider({ children }) {
  return children;
}

export function useT() {
  const t = (text, vars = {}) =>
    text.replace(/\{(\w+)\}/g, (_, k) => (k in vars ? vars[k] : `{${k}}`));
  return { t, locale: "en-GB" };
}
