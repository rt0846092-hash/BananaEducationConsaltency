import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { OFFICE } from "../config";
import { useT } from "../i18n";
import { usePageMeta } from "../seo";

const QUALIFICATIONS = [
  "+2 / A-Levels", "Diploma", "Bachelor's degree", "Master's degree", "Other",
];

export default function Apply() {
  const { t } = useT();
  const [params] = useSearchParams();
  const [step, setStep] = useState(1);
  const [countries, setCountries] = useState([]);
  const [token, setToken] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  usePageMeta({
    title: "Free study abroad counselling",
    description: "Three questions, thirty seconds. A counsellor calls you back within one working day — free, with no obligation to apply.",
  });

  // ?country=3 comes from tapping a destination on the home page.
  // ?src=fair-jan comes from whichever printed QR code was scanned, so the
  // owner can see which poster, branch or education fair actually produced
  // students. Same form, different tag.
  const preselected = params.get("country");
  const source = params.get("src") || "website";

  const [one, setOne] = useState({
    full_name: "", phone: "", email: "",
    interested_countries: preselected ? [Number(preselected)] : [],
    consent_given: false,
    website: "", // honeypot — left blank by humans, filled by bots
  });

  const [two, setTwo] = useState({
    highest_qualification: "", completion_year: "", study_gap_years: "",
    test_type: "none", test_score: "", target_intake: "", budget_note: "",
    visa_history: "none", visa_history_country: "", message: "",
  });

  useEffect(() => {
    api.countries().then(setCountries).catch(() => {});
  }, []);

  function toggleCountry(id) {
    setOne((prev) => ({
      ...prev,
      interested_countries: prev.interested_countries.includes(id)
        ? prev.interested_countries.filter((c) => c !== id)
        : [...prev.interested_countries, id],
    }));
  }

  async function submitStepOne(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const res = await api.startIntake({ ...one, source });
      setToken(res.token);
      setStep(2);
      window.scrollTo(0, 0);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function submitStepTwo(e) {
    e.preventDefault();
    setBusy(true);
    try {
      // Blank optional fields would fail number validation on the server,
      // so only send what was actually filled in.
      const filled = Object.fromEntries(
        Object.entries(two).filter(([, v]) => v !== "" && v !== null)
      );
      // A score typed before switching back to "no test" shouldn't be sent.
      if (filled.test_type === "none") delete filled.test_score;
      if (filled.visa_history !== "refused") delete filled.visa_history_country;
      await api.finishIntake(token, filled);
    } catch {
      // Their contact details are already saved. Losing the optional extras
      // is not worth showing them an error and making them think it failed.
    } finally {
      setBusy(false);
      setStep(3);
      window.scrollTo(0, 0);
    }
  }

  if (step === 3) {
    return (
      <div className="wrap max-w-prose py-20 text-center">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-grass-pale">
          <span className="text-2xl text-grass">✓</span>
        </div>
        <h1 className="mt-6 text-3xl">{t("We have your details")}</h1>
        <p className="mt-3 leading-relaxed text-navy-soft">
          {t("A counsellor will call you on {phone} within one working day. If you'd rather not wait, the office is open Sunday to Friday, 10 am to 6 pm.", { phone: one.phone })}
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <a href={`tel:${OFFICE.phoneTel}`} className="btn-go">{t("Call the office now")}</a>
          <Link to="/" className="btn-quiet">{t("Back to the site")}</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="wrap max-w-2xl py-12">
      <div className="mb-8 flex gap-2" aria-hidden="true">
        <div className="h-1 flex-1 rounded bg-grass" />
        <div className={`h-1 flex-1 rounded ${step === 2 ? "bg-grass" : "bg-rule"}`} />
      </div>

      {step === 1 ? (
        <form onSubmit={submitStepOne} noValidate>
          <h1 className="text-3xl">{t("Free counselling")}</h1>
          <p className="mt-2 text-navy-soft">{t("Three questions. It takes about thirty seconds.")}</p>

          <div className="mt-8 space-y-5">
            <div>
              <label className="label" htmlFor="name">{t("Your full name")}</label>
              <input
                id="name" className="field" required autoComplete="name"
                value={one.full_name}
                onChange={(e) => setOne({ ...one, full_name: e.target.value })}
              />
            </div>

            <div>
              <label className="label" htmlFor="phone">{t("Phone number")}</label>
              <input
                id="phone" className="field" required type="tel" autoComplete="tel"
                inputMode="tel" placeholder="98…"
                value={one.phone}
                onChange={(e) => setOne({ ...one, phone: e.target.value })}
              />
              <p className="mt-1.5 text-sm text-navy-soft">
                {t("This is how a counsellor will reach you.")}
              </p>
            </div>

            <fieldset>
              <legend className="label">{t("Where do you want to study?")}</legend>
              <div className="flex flex-wrap gap-2">
                {countries.map((c) => {
                  const on = one.interested_countries.includes(c.id);
                  return (
                    <button
                      type="button" key={c.id} onClick={() => toggleCountry(c.id)}
                      aria-pressed={on}
                      className={`rounded-full border px-4 py-2 text-sm transition-colors ${
                        on
                          ? "border-grass bg-grass text-white"
                          : "border-rule bg-white text-navy hover:border-navy-soft"
                      }`}
                    >
                      {c.name}
                    </button>
                  );
                })}
              </div>
              <p className="mt-2 text-sm text-navy-soft">
                {t("Pick more than one if you're still deciding.")}
              </p>
            </fieldset>

            {/* Hidden from people, irresistible to bots. */}
            <div className="hidden" aria-hidden="true">
              <label htmlFor="website">Website</label>
              <input
                id="website" tabIndex={-1} autoComplete="off"
                value={one.website}
                onChange={(e) => setOne({ ...one, website: e.target.value })}
              />
            </div>

            <div className="flex gap-3 rounded-md border border-rule bg-white p-4">
              <input
                id="consent" type="checkbox" required className="mt-1 h-4 w-4 shrink-0 accent-grass"
                checked={one.consent_given}
                onChange={(e) => setOne({ ...one, consent_given: e.target.checked })}
              />
              <div className="text-sm leading-relaxed text-navy">
                <label htmlFor="consent">
                  {t("{office} can contact me by phone about studying abroad. We keep your details private and never sell them.", { office: OFFICE.name })}
                </label>{" "}
                <Link to="/privacy" target="_blank" className="font-medium text-grass underline underline-offset-2">
                  {t("How we use your details")}
                </Link>
              </div>
            </div>
          </div>

          {error && (
            <p className="mt-5 rounded-md border border-urgent/30 bg-urgent/5 px-4 py-3 text-sm text-urgent">
              {t(error, { phone: OFFICE.phone })}
            </p>
          )}

          <button type="submit" disabled={busy} className="btn-go mt-6 w-full sm:w-auto">
            {busy ? t("Saving…") : t("Continue")}
          </button>
        </form>
      ) : (
        <form onSubmit={submitStepTwo}>
          <h1 className="text-3xl">{t("A little more about you")}</h1>
          <p className="mt-2 leading-relaxed text-navy-soft">
            {t("All of this is optional, and we already have your contact details. Answering helps the counsellor come prepared instead of asking you on the phone.")}
          </p>

          <div className="mt-8 space-y-5">
            <div className="grid gap-5 sm:grid-cols-2">
              <div>
                <label className="label" htmlFor="qual">{t("Highest qualification")}</label>
                <select
                  id="qual" className="field" value={two.highest_qualification}
                  onChange={(e) => setTwo({ ...two, highest_qualification: e.target.value })}
                >
                  <option value="">{t("Choose one")}</option>
                  {QUALIFICATIONS.map((q) => <option key={q} value={q}>{q}</option>)}
                </select>
              </div>
              <div>
                <label className="label" htmlFor="year">{t("Year completed (AD)")}</label>
                <input
                  id="year" className="field" type="number" inputMode="numeric"
                  min="1980" max="2035" placeholder="2024"
                  value={two.completion_year}
                  onChange={(e) => setTwo({ ...two, completion_year: e.target.value })}
                />
              </div>
            </div>

            <div>
              <label className="label" htmlFor="gap">{t("Years since you last studied")}</label>
              <input
                id="gap" className="field" type="number" inputMode="numeric" min="0" max="30"
                value={two.study_gap_years}
                onChange={(e) => setTwo({ ...two, study_gap_years: e.target.value })}
              />
              <p className="mt-1.5 text-sm text-navy-soft">
                {t("A gap is normal and it doesn't disqualify you. It just changes what we need to explain in the application.")}
              </p>
            </div>

            <div className="grid gap-5 sm:grid-cols-2">
              <div>
                <label className="label" htmlFor="test">{t("English or Korean test")}</label>
                <select
                  id="test" className="field" value={two.test_type}
                  onChange={(e) => setTwo({ ...two, test_type: e.target.value })}
                >
                  <option value="none">{t("Haven't taken one yet")}</option>
                  <option value="ielts">IELTS</option>
                  <option value="pte">PTE</option>
                  <option value="toefl">TOEFL</option>
                  <option value="topik">TOPIK</option>
                </select>
              </div>
              {two.test_type !== "none" && (
                <div>
                  <label className="label" htmlFor="score">{t("Your score")}</label>
                  <input
                    id="score" className="field" inputMode="decimal" placeholder="6.5"
                    value={two.test_score}
                    onChange={(e) => setTwo({ ...two, test_score: e.target.value })}
                  />
                </div>
              )}
            </div>

            {/* Asked as "have you applied before?", never "were you rejected?".
                People find the second accusatory and either lie or abandon the
                form — and prior refusal is exactly what the counsellor most
                needs to know before the first call. */}
            <fieldset className="rounded-md border border-rule bg-white p-4">
              <legend className="label px-1">{t("Have you applied for a student visa before?")}</legend>
              <div className="space-y-2.5">
                {[
                  ["none", "No, this is my first time"],
                  ["approved", "Yes, and it was approved"],
                  ["refused", "Yes, and it was refused"],
                ].map(([value, text]) => (
                  <label key={value} className="flex items-center gap-3 text-sm text-navy">
                    <input
                      type="radio" name="visa" value={value}
                      className="h-4 w-4 accent-grass"
                      checked={two.visa_history === value}
                      onChange={() => setTwo({ ...two, visa_history: value })}
                    />
                    {t(text)}
                  </label>
                ))}
              </div>

              {two.visa_history === "refused" && (
                <div className="mt-4 border-t border-rule pt-4">
                  <label className="label" htmlFor="refused-where">{t("Which country?")}</label>
                  <input
                    id="refused-where" className="field"
                    value={two.visa_history_country}
                    onChange={(e) => setTwo({ ...two, visa_history_country: e.target.value })}
                  />
                  <p className="mt-2 text-sm leading-relaxed text-navy-soft">
                    {t("A refusal doesn't end your plans. Knowing about it now means we build the next application to answer it directly.")}
                  </p>
                </div>
              )}
            </fieldset>

            <div>
              <label className="label" htmlFor="message">{t("Anything else we should know?")}</label>
              <textarea
                id="message" className="field" rows={3}
                value={two.message}
                onChange={(e) => setTwo({ ...two, message: e.target.value })}
              />
            </div>
          </div>

          <div className="mt-6 flex flex-wrap gap-3">
            <button type="submit" disabled={busy} className="btn-go">
              {busy ? t("Saving…") : t("Finish")}
            </button>
            <button type="button" onClick={() => setStep(3)} className="btn-quiet">
              {t("Skip this")}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
