/**
 * Runs after `vite build`. Adds what search engines need to a single-page app:
 *
 *   dist/robots.txt   — index the public pages, stay out of /staff
 *   dist/sitemap.xml  — every public page, one per destination
 *   dist/index.html   — absolute share-image URL, Google verification tag,
 *                       and structured data describing the business
 *
 * VITE_SITE_URL is the public address, e.g. https://www.bananaeducation.com.np
 * The destination list is read from the API; if the API is asleep or down the
 * build still succeeds, with the fixed pages only.
 */
import { readFileSync, writeFileSync } from "node:fs";

const env = process.env;
const site = (env.VITE_SITE_URL || env.RENDER_EXTERNAL_URL || "").replace(/\/$/, "");
const api = (env.VITE_API_URL || "").replace(/\/$/, "");
const office = {
  name: env.VITE_OFFICE_NAME || "Banana Education",
  phone: env.VITE_OFFICE_PHONE_TEL || "+97715551234",
  email: env.VITE_OFFICE_EMAIL || "hello@banana.demo",
  street: env.VITE_OFFICE_STREET || "Putalisadak",
  city: env.VITE_OFFICE_CITY || "Kathmandu",
  country: env.VITE_OFFICE_COUNTRY || "NP",
};

if (!site) {
  console.warn("seo: VITE_SITE_URL not set — skipping robots.txt and sitemap.xml.");
  process.exit(0);
}

async function destinations() {
  if (!api) return [];
  try {
    const res = await fetch(`${api}/countries/`, { signal: AbortSignal.timeout(90_000) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return (await res.json()).map((c) => c.slug);
  } catch (err) {
    console.warn(`seo: couldn't read destinations from the API (${err.message}); sitemap has the main pages only.`);
    return [];
  }
}

const today = new Date().toISOString().slice(0, 10);
const pages = [
  ["/", "1.0"], ["/apply", "0.9"], ["/privacy", "0.3"],
  ...(await destinations()).map((slug) => [`/study/${slug}`, "0.8"]),
];

writeFileSync("dist/sitemap.xml",
  `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n` +
  pages.map(([p, pr]) => `  <url><loc>${site}${p}</loc><lastmod>${today}</lastmod><priority>${pr}</priority></url>`).join("\n") +
  `\n</urlset>\n`);

writeFileSync("dist/robots.txt",
  `User-agent: *\nAllow: /\nDisallow: /staff\n\nSitemap: ${site}/sitemap.xml\n`);

let html = readFileSync("dist/index.html", "utf8");
// Facebook and WhatsApp need a full address for the preview image.
html = html.replace('content="/og-image.png"', `content="${site}/og-image.png"`);
html = html.replace("</head>", [
  `    <meta property="og:url" content="${site}/" />`,
  env.VITE_GOOGLE_SITE_VERIFICATION
    ? `    <meta name="google-site-verification" content="${env.VITE_GOOGLE_SITE_VERIFICATION}" />`
    : "",
  // Lets Google show the business name, phone and address in results.
  `    <script type="application/ld+json">${JSON.stringify({
    "@context": "https://schema.org",
    "@type": "EducationalOrganization",
    name: office.name,
    url: `${site}/`,
    logo: `${site}/icon-512.png`,
    telephone: office.phone,
    email: office.email,
    address: { "@type": "PostalAddress", streetAddress: office.street,
               addressLocality: office.city, addressCountry: office.country },
  })}</script>`,
  "  </head>",
].filter(Boolean).join("\n"));
writeFileSync("dist/index.html", html);

console.log(`seo: sitemap with ${pages.length} pages for ${site}`);
