import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { staffApi } from "../auth";

const SOURCES = [
  ["walk-in", "Walked into the office"],
  ["phone-call", "Phoned the office"],
  ["referral", "Referred by someone"],
  ["facebook", "Facebook"],
  ["whatsapp", "WhatsApp"],
  ["instagram", "Instagram"],
  ["event", "Education fair or event"],
  ["other", "Other"],
];

/**
 * For students who never touched the website: walk-ins, phone calls,
 * referrals. A counsellor's new student is always theirs; the owner can hand
 * it to anyone. Consent is still recorded — same personal data, whichever door
 * it came through.
 */
export default function AddStudent() {
  const navigate = useNavigate();
  const [me, setMe] = useState(null);
  const [countries, setCountries] = useState([]);
  const [staff, setStaff] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [existingId, setExistingId] = useState(null);
  const [form, setForm] = useState({
    full_name: "", phone: "", email: "", interested_countries: [],
    source: "walk-in", source_detail: "", consent_given: false, consent_method: "verbal",
    assigned_to: "", target_intake: "", highest_qualification: "", message: "",
    next_follow_up: "",
  });
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  useEffect(() => {
    const bail = (err) => {
      if (err.message === "SESSION_EXPIRED") navigate("/staff/login");
      if (err.message === "PASSWORD_CHANGE_REQUIRED") navigate("/staff/password");
    };
    Promise.all([staffApi.me(), staffApi.countries()])
      .then(([u, c]) => {
        setMe(u);
        setCountries(c);
        if (u.is_admin) staffApi.team().then(setStaff).catch(() => {});
      })
      .catch(bail);
  }, [navigate]);

  function toggleCountry(id) {
    const list = form.interested_countries;
    setForm({
      ...form,
      interested_countries: list.includes(id) ? list.filter((c) => c !== id) : [...list, id],
    });
  }

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setExistingId(null);
    const data = Object.fromEntries(
      Object.entries(form).filter(([, v]) => v !== "" && v !== null)
    );
    if (data.assigned_to) data.assigned_to = Number(data.assigned_to);
    try {
      const lead = await staffApi.addLead(data);
      navigate(`/staff/leads/${lead.id}`);
    } catch (err) {
      if (err.message === "SESSION_EXPIRED") return navigate("/staff/login");
      setError(err.message);
      setExistingId(err.body?.existing_id || null);
      setBusy(false);
    }
  }

  return (
    <div className="wrap max-w-2xl py-8">
      <Link to="/staff" className="text-sm text-navy-soft hover:text-grass">Back to the list</Link>
      <h1 className="mt-4 text-2xl sm:text-3xl">Add a student</h1>
      <p className="mt-1.5 text-navy-soft">
        For walk-ins, phone calls and referrals — anyone who didn't fill in the website form.
        {me && !me.is_admin && " They'll be added to your list."}
      </p>

      <form onSubmit={submit} className="mt-8 space-y-5">
        <div className="grid gap-5 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="name">Full name</label>
            <input id="name" className="field" required value={form.full_name} onChange={set("full_name")} />
          </div>
          <div>
            <label className="label" htmlFor="phone">Phone</label>
            <input id="phone" className="field" required type="tel" value={form.phone} onChange={set("phone")} />
          </div>
        </div>

        <div>
          <label className="label" htmlFor="email">Email <span className="font-normal text-navy-soft">(optional)</span></label>
          <input id="email" className="field" type="email" value={form.email} onChange={set("email")} />
        </div>

        <fieldset>
          <legend className="label">Interested in</legend>
          <div className="flex flex-wrap gap-2">
            {countries.map((c) => {
              const on = form.interested_countries.includes(c.id);
              return (
                <button
                  type="button" key={c.id} onClick={() => toggleCountry(c.id)} aria-pressed={on}
                  className={`rounded-full border px-4 py-2 text-sm ${
                    on ? "border-grass bg-grass text-white" : "border-rule bg-white text-navy hover:border-navy-soft"
                  }`}
                >
                  {c.name}
                </button>
              );
            })}
          </div>
        </fieldset>

        <div className="grid gap-5 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="source">How they reached us</label>
            <select id="source" className="field" value={form.source} onChange={set("source")}>
              {SOURCES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </div>
          <div>
            <label className="label" htmlFor="detail">Details <span className="font-normal text-navy-soft">(optional)</span></label>
            <input
              id="detail" className="field" placeholder="e.g. referred by Anisha Gurung"
              value={form.source_detail} onChange={set("source_detail")}
            />
          </div>
        </div>

        <div className="grid gap-5 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="intake">Target intake</label>
            <input id="intake" className="field" placeholder="Sep 2027" value={form.target_intake} onChange={set("target_intake")} />
          </div>
          <div>
            <label className="label" htmlFor="qual">Highest qualification</label>
            <input id="qual" className="field" placeholder="+2 Science" value={form.highest_qualification} onChange={set("highest_qualification")} />
          </div>
        </div>

        <div>
          <label className="label" htmlFor="msg">What they told you</label>
          <textarea id="msg" className="field" rows={3} value={form.message} onChange={set("message")} />
        </div>

        <div className="grid gap-5 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="follow">Next follow-up</label>
            <input id="follow" type="date" className="field" value={form.next_follow_up} onChange={set("next_follow_up")} />
          </div>
          {me?.is_admin && (
            <div>
              <label className="label" htmlFor="assign">Assign to</label>
              <select id="assign" className="field" value={form.assigned_to} onChange={set("assigned_to")}>
                <option value="">Nobody yet</option>
                {staff.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </div>
          )}
        </div>

        <fieldset className="rounded-md border border-rule bg-white p-4">
          <label className="flex gap-3 text-sm leading-relaxed text-navy">
            <input
              type="checkbox" className="mt-1 h-4 w-4 accent-grass" checked={form.consent_given}
              onChange={(e) => setForm({ ...form, consent_given: e.target.checked })}
            />
            The student agreed that we can keep their details and contact them about studying
            abroad.
          </label>
          <div className="mt-3 flex flex-wrap gap-5 pl-7 text-sm text-navy">
            {[["verbal", "Told me in person or on the phone"], ["written", "Signed a form"]].map(([v, l]) => (
              <label key={v} className="flex items-center gap-2">
                <input
                  type="radio" name="consent_method" className="accent-grass"
                  checked={form.consent_method === v}
                  onChange={() => setForm({ ...form, consent_method: v })}
                />
                {l}
              </label>
            ))}
          </div>
        </fieldset>

        {error && (
          <div className="rounded-md border border-urgent/30 bg-urgent/5 px-4 py-3 text-sm text-urgent">
            {error}
            {existingId && (
              <Link to={`/staff/leads/${existingId}`} className="ml-2 font-medium underline">
                Open their record
              </Link>
            )}
          </div>
        )}

        <button className="btn-go" disabled={busy}>{busy ? "Saving…" : "Add student"}</button>
      </form>
    </div>
  );
}
