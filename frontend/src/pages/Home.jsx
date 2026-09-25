import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { OFFICE } from "../config";
import { useT } from "../i18n";
import { usePageMeta } from "../seo";

const STEPS = [
  ["Tell us where you want to go", "One short form, or walk into the office."],
  ["Sit down with a counsellor", "Free, and no obligation to apply."],
  ["Build your file", "Transcripts, funds, test scores, statement of purpose."],
  ["Apply and file the visa", "We track every deadline so you don't have to."],
];

/**
 * Each card opens the country page, where the universities, fees and
 * scholarships are. Previously the cards went straight to the form, so no
 * visitor could reach those pages without typing the address.
 */
function Destinations({ countries }) {
  const { t } = useT();
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {countries.map((c) => (
        <Link
          key={c.slug}
          to={`/study/${c.slug}`}
          className="group rounded-lg border border-rule bg-white p-5 text-left
                     hover:border-grass focus-visible:border-grass"
        >
          <div className="font-display text-xl font-semibold text-navy-deep group-hover:text-grass">
            {c.name}
          </div>
          <p className="mt-1.5 text-sm leading-relaxed text-navy-soft">{c.summary}</p>
          <div className="mt-3 text-sm font-medium text-grass">
            {t("{n} partner universities", { n: c.university_count })} →
          </div>
        </Link>
      ))}
    </div>
  );
}

export default function Home() {
  const { t, locale } = useT();
  const [countries, setCountries] = useState([]);
  const [batches, setBatches] = useState([]);
  const [counsellors, setCounsellors] = useState([]);
  const [failed, setFailed] = useState(false);
  usePageMeta({
    title: "Study abroad counselling in Kathmandu",
    description: `Free counselling for studying in Australia, the USA, the UK, South Korea and Europe. Universities, fees, scholarships and IELTS/PTE classes at ${OFFICE.name}.`,
  });

  useEffect(() => {
    Promise.all([api.countries(), api.batches(), api.counsellors()])
      .then(([c, b, s]) => {
        setCountries(c);
        setBatches(b);
        setCounsellors(s);
      })
      .catch(() => setFailed(true));
  }, []);

  if (failed) {
    return (
      <div className="wrap py-24 text-center">
        <h1 className="text-2xl">{t("The site can't reach our servers")}</h1>
        <p className="mx-auto mt-3 max-w-prose text-navy-soft">
          {t("Call us on {phone} and we'll help you straight away.", { phone: OFFICE.phone })}
        </p>
      </div>
    );
  }

  return (
    <>
      {/* The hero is the first question of the form, not a picture of
          graduates throwing their caps. */}
      <section className="border-b border-rule bg-white">
        <div className="wrap py-16 sm:py-20">
          <h1 className="max-w-prose text-3xl leading-tight sm:text-5xl sm:leading-[1.15]">
            {t("Where do you want to study?")}
          </h1>
          <p className="mt-4 max-w-prose text-lg leading-relaxed text-navy-soft">
            {t("Pick a country and we'll call you back the same day. Counselling is free, and you're not committing to anything by asking.")}
          </p>

          <div className="mt-8">
            {countries.length ? (
              <Destinations countries={countries} />
            ) : (
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {[0, 1, 2, 3, 4].map((i) => (
                  <div key={i} className="h-32 rounded-lg border border-rule bg-paper" />
                ))}
              </div>
            )}
          </div>

          <div className="mt-8 flex flex-wrap items-center gap-x-4 gap-y-3">
            <Link to="/apply" className="btn-go">{t("Free counselling")}</Link>
            <p className="text-sm text-navy-soft">
              {t("Not sure yet?")}{" "}
              <Link to="/apply" className="font-medium text-grass underline underline-offset-2">
                {t("Book a counselling session")}
              </Link>{" "}
              {t("and we'll work it out together.")}
            </p>
          </div>
        </div>
      </section>

      {/* Genuinely a sequence, so numbering it carries information. */}
      <section className="wrap py-16">
        <h2 className="text-2xl sm:text-3xl">{t("How this works")}</h2>
        <ol className="mt-8 grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map(([title, detail], i) => (
            <li key={title} className="border-t-2 border-grass pt-4">
              <div className="font-display text-sm font-semibold text-grass">
                {t("Step {n}", { n: i + 1 })}
              </div>
              <h3 className="mt-1 text-lg">{t(title)}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-navy-soft">{t(detail)}</p>
            </li>
          ))}
        </ol>
      </section>

      {batches.length > 0 && (
        <section className="border-y border-rule bg-white">
          <div className="wrap py-16">
            <h2 className="text-2xl sm:text-3xl">{t("Language classes starting soon")}</h2>
            <p className="mt-2 max-w-prose text-navy-soft">
              {t("IELTS, PTE and TOPIK preparation in small groups.")}
            </p>
            <div className="mt-8 divide-y divide-rule border-y border-rule">
              {batches.map((b) => (
                <div
                  key={b.id}
                  className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2 py-4"
                >
                  <div>
                    <div className="font-display text-lg font-semibold text-navy-deep">
                      {t("{test} preparation", { test: b.test_type_display })}
                    </div>
                    <div className="text-sm text-navy-soft">
                      {b.schedule_note} · {t("{n} weeks", { n: b.duration_weeks })}
                    </div>
                  </div>
                  <div className="text-right text-sm">
                    <div className="font-medium text-navy">
                      {t("Starts {date}", {
                        date: new Date(b.start_date).toLocaleDateString(locale, {
                          day: "numeric", month: "short",
                        }),
                      })}
                    </div>
                    {/* Amber is reserved for anything with a clock on it. */}
                    <div className={b.seats_left <= 5 ? "text-urgent" : "text-navy-soft"}>
                      {t("{n} seats left", { n: b.seats_left })}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {counsellors.length > 0 && (
        <section className="wrap py-16">
          <h2 className="text-2xl sm:text-3xl">{t("The people you'll be talking to")}</h2>
          <div className="mt-8 grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
            {counsellors.map((p) => (
              <div key={p.id}>
                <h3 className="text-lg">{p.name}</h3>
                <p className="mt-1 text-sm text-grass">{p.languages}</p>
                <p className="mt-2 text-sm leading-relaxed text-navy-soft">{p.bio}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="bg-grass-pale">
        <div className="wrap py-14">
          <h2 className="text-2xl sm:text-3xl">{t("Been refused a visa before?")}</h2>
          <p className="mt-3 max-w-prose leading-relaxed text-navy">
            {t("It doesn't end your plans, but it does change how the next application has to be built. Tell us what happened when you fill in the form and we'll be honest with you about what's realistic.")}
          </p>
          <Link to="/apply" className="btn-go mt-6">
            {t("Start your form")}
          </Link>
        </div>
      </section>
    </>
  );
}
