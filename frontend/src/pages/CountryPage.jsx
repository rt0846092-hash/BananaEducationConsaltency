import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { useT } from "../i18n";

const money = (amount, currency) =>
  new Intl.NumberFormat("en-US", {
    style: "currency", currency: currency || "USD", maximumFractionDigits: 0,
  }).format(amount);

export default function CountryPage() {
  const { slug } = useParams();
  const { t, locale } = useT();
  const longDate = (d) =>
    new Date(d).toLocaleDateString(locale, { day: "numeric", month: "long", year: "numeric" });
  const [country, setCountry] = useState(null);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    setCountry(null);
    setMissing(false);
    api.country(slug).then(setCountry).catch(() => setMissing(true));
  }, [slug]);

  if (missing) {
    return (
      <div className="wrap max-w-prose py-24 text-center">
        <h1 className="text-2xl">{t("We don't have a page for that destination")}</h1>
        <Link to="/" className="btn-quiet mt-6">{t("See where we do send students")}</Link>
      </div>
    );
  }

  if (!country) {
    return <div className="wrap py-24 text-navy-soft">{t("Loading…")}</div>;
  }

  return (
    <>
      <section className="border-b border-rule bg-white">
        <div className="wrap py-14">
          <h1 className="text-3xl sm:text-4xl">{t("Studying in {name}", { name: country.name })}</h1>
          <p className="mt-4 max-w-prose text-lg leading-relaxed text-navy-soft">
            {country.summary}
          </p>
          <Link to={`/apply?country=${country.id}`} className="btn-go mt-7">
            {t("Talk to a {name} counsellor", { name: country.name })}
          </Link>
        </div>
      </section>

      {country.visa_notes && (
        <section className="bg-grass-pale">
          <div className="wrap py-10">
            <h2 className="text-xl">{t("What the visa asks for")}</h2>
            <p className="mt-2 max-w-prose leading-relaxed text-navy">{country.visa_notes}</p>
          </div>
        </section>
      )}

      <section className="wrap py-14">
        <h2 className="text-2xl sm:text-3xl">{t("Universities we work with")}</h2>
        <div className="mt-8 space-y-px">
          {country.universities.map((u) => (
            <article key={u.id} className="border-t border-rule py-6">
              <div className="flex flex-wrap items-baseline justify-between gap-3">
                <h3 className="text-xl">{u.name}</h3>
                <span className="text-sm text-navy-soft">{u.city}</span>
              </div>

              {u.courses.length > 0 && (
                <ul className="mt-4 divide-y divide-rule/60 border-y border-rule/60">
                  {u.courses.map((c) => (
                    <li
                      key={c.id}
                      className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 py-2.5"
                    >
                      <span className="text-navy">{c.name}</span>
                      <span className="text-sm text-navy-soft">
                        {c.duration_months != null && t("{n} months", { n: c.duration_months })}
                        {c.tuition_fee != null &&
                          ` · ${t("about {amount} total", { amount: money(c.tuition_fee, c.currency) })}`}
                      </span>
                    </li>
                  ))}
                </ul>
              )}

              {/* Families make expensive decisions on these numbers, so the
                  page says out loud how fresh they are. */}
              {u.last_verified_on && (
                <p className="mt-3 text-sm text-navy-soft">
                  {t("Fees checked {date}. Confirm with the university before you pay anything.", {
                    date: longDate(u.last_verified_on),
                  })}
                </p>
              )}
            </article>
          ))}
        </div>
      </section>

      {country.scholarships.length > 0 && (
        <section className="border-t border-rule bg-white">
          <div className="wrap py-14">
            <h2 className="text-2xl sm:text-3xl">{t("Scholarships")}</h2>
            <div className="mt-8 space-y-6">
              {country.scholarships.map((s) => (
                <div key={s.id} className="border-l-2 border-grass pl-5">
                  <h3 className="text-lg">{s.name}</h3>
                  <p className="text-sm font-medium text-grass">{s.amount_note}</p>
                  <p className="mt-1.5 max-w-prose text-sm leading-relaxed text-navy-soft">
                    {s.eligibility}
                  </p>
                  {s.deadline && (
                    <p className="mt-1.5 text-sm text-urgent">
                      {t("Closes {date}", { date: longDate(s.deadline) })}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        </section>
      )}
    </>
  );
}
