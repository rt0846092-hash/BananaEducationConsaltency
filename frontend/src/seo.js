/**
 * Page titles and descriptions for search results.
 *
 * This is a single-page app, so without this every page had the same title
 * and no description, and Google showed them all identically. Google runs the
 * JavaScript before indexing, so setting these here is enough.
 */
import { useEffect } from "react";
import { OFFICE } from "./config";

function setMeta(selector, attr, name, value) {
  let el = document.head.querySelector(selector);
  if (!value) {
    if (el) el.remove();
    return;
  }
  if (!el) {
    el = document.createElement(selector.startsWith("link") ? "link" : "meta");
    el.setAttribute(attr, name);
    document.head.appendChild(el);
  }
  el.setAttribute(selector.startsWith("link") ? "href" : "content", value);
}

/**
 * usePageMeta({ title, description, noindex })
 * title        — shown as the blue link in Google; the office name is added.
 * description  — the grey text under it (aim for 120–160 characters).
 * noindex      — keep this page out of search results (staff area, 404s).
 */
export function usePageMeta({ title, description, noindex = false }) {
  useEffect(() => {
    document.title = title ? `${title} | ${OFFICE.name}` : `${OFFICE.name} — study abroad counselling`;
    setMeta('meta[name="description"]', "name", "description", description);
    setMeta('meta[property="og:title"]', "property", "og:title", document.title);
    if (description) setMeta('meta[property="og:description"]', "property", "og:description", description);
    setMeta('meta[name="robots"]', "name", "robots", noindex ? "noindex, nofollow" : "");
    // One address per page, so Google doesn't treat ?src=fair-jan as a copy.
    setMeta('link[rel="canonical"]', "rel", "canonical",
            noindex ? "" : window.location.origin + window.location.pathname);
  }, [title, description, noindex]);
}
