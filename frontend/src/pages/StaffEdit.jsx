import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { staffApi } from "../auth";

/** A readable temporary password: no 0/O or 1/l to misread over the phone. */
function suggestPassword() {
  const chars = "ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789";
  const pick = (n) =>
    Array.from(crypto.getRandomValues(new Uint32Array(n)), (x) => chars[x % chars.length]).join("");
  return `${pick(4)}-${pick(4)}-${pick(4)}`;
}

function Notice({ tone = "error", children }) {
  if (!children) return null;
  const cls = tone === "ok"
    ? "border-grass/30 bg-grass-pale text-grass-dark"
    : "border-urgent/30 bg-urgent/5 text-urgent";
  return <div className={`rounded-md border px-4 py-3 text-sm ${cls}`}>{children}</div>;
}

/**
 * Owner only. Add a counsellor, or change someone's details, the countries
 * they receive new students for, their password (when forgotten) and whether
 * their account is open. Accounts are closed, never deleted.
 */
export default function StaffEdit() {
  const { id } = useParams();
  const isNew = !id;
  const navigate = useNavigate();
  const [me, setMe] = useState(null);
  const [countries, setCountries] = useState([]);
  const [person, setPerson] = useState(null);
  const [form, setForm] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState("");
  const [created, setCreated] = useState(null);
  const [newPassword, setNewPassword] = useState("");
  const [resetDone, setResetDone] = useState("");

  const fail = (err) => {
    if (err.message === "SESSION_EXPIRED") navigate("/staff/login");
    else setError(err.message);
  };

  useEffect(() => {
    Promise.all([staffApi.me(), staffApi.countries(), isNew ? null : staffApi.staffGet(id)])
      .then(([u, c, p]) => {
        setMe(u);
        setCountries(c);
        const base = p || {
          username: "", first_name: "", last_name: "", email: "", phone: "",
          role: "counsellor", languages: "", bio: "", is_public: true,
          auto_assign: true, countries: [],
        };
        setPerson(p);
        setForm({ ...base, password: isNew ? suggestPassword() : "" });
      })
      .catch(fail);
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  if (error && !form) return <p className="wrap py-20 text-urgent">{error}</p>;
  if (!form) return <p className="wrap py-20 text-navy-soft">Loading…</p>;
  if (me && !me.is_admin) return <p className="wrap py-20 text-urgent">This page is for the office owner.</p>;

  const set = (k) => (e) =>
    setForm({ ...form, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });
  const toggleCountry = (cid) =>
    setForm({
      ...form,
      countries: form.countries.includes(cid)
        ? form.countries.filter((c) => c !== cid)
        : [...form.countries, cid],
    });
  const isSelf = person && me && person.id === me.id;

  async function save(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setSaved("");
    const { password, ...rest } = form;
    const fields = ["username", "first_name", "last_name", "email", "phone", "role",
                    "languages", "bio", "is_public", "auto_assign", "countries"];
    const data = Object.fromEntries(fields.map((k) => [k, rest[k]]));
    try {
      if (isNew) {
        const p = await staffApi.staffAdd({ ...data, password });
        setCreated({ ...p, password });
      } else {
        const p = await staffApi.staffUpdate(id, data);
        setPerson(p);
        setSaved("Saved.");
      }
    } catch (err) {
      fail(err);
    } finally {
      setBusy(false);
    }
  }

  async function resetPassword(e) {
    e.preventDefault();
    setError("");
    setResetDone("");
    try {
      await staffApi.staffResetPassword(id, newPassword);
      setResetDone(newPassword);
      setNewPassword("");
    } catch (err) {
      fail(err);
    }
  }

  async function toggleActive() {
    setError("");
    setSaved("");
    try {
      const p = person.is_active
        ? await staffApi.staffDeactivate(id)
        : await staffApi.staffReactivate(id);
      setPerson(p);
      setSaved(p.is_active ? "Account reopened. They can sign in again." : "Account closed.");
    } catch (err) {
      fail(err);
    }
  }

  // After adding someone: show the sign-in details once, to pass on.
  if (created) {
    return (
      <div className="wrap max-w-xl py-10">
        <h1 className="text-2xl">{created.first_name || created.username} can now sign in</h1>
        <p className="mt-2 text-navy-soft">
          Give them these details. They'll be asked to choose their own password the first
          time they sign in.
        </p>
        <dl className="mt-6 space-y-3 rounded-lg border border-rule bg-white p-5">
          <div><dt className="text-sm text-navy-soft">Sign in at</dt>
            <dd className="text-navy">{window.location.origin}/staff/login</dd></div>
          <div><dt className="text-sm text-navy-soft">Username</dt>
            <dd className="font-mono text-lg text-navy-deep">{created.username}</dd></div>
          <div><dt className="text-sm text-navy-soft">Temporary password</dt>
            <dd className="font-mono text-lg text-navy-deep">{created.password}</dd></div>
        </dl>
        <p className="mt-3 text-sm text-navy-soft">
          This password isn't shown again. If it's lost, use "Reset password" on their page.
        </p>
        <div className="mt-6 flex gap-3">
          <Link to="/staff/team" className="btn-go">Back to the team</Link>
          <Link to={`/staff/team/${created.id}`} className="btn-quiet">Edit {created.first_name || created.username}</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="wrap max-w-2xl py-8">
      <Link to="/staff/team" className="text-sm text-navy-soft hover:text-grass">Back to the team</Link>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl sm:text-3xl">
          {isNew ? "Add a staff member" : person.first_name || person.username}
        </h1>
        {!isNew && (
          <span className={`rounded-full border px-3 py-1 text-sm ${
            person.is_active ? "border-grass/30 bg-grass-pale text-grass-dark" : "border-rule bg-paper text-navy-soft"}`}>
            {person.is_active ? (person.must_change_password ? "Hasn't signed in yet" : "Active") : "Closed"}
          </span>
        )}
      </div>

      <form onSubmit={save} className="mt-6 space-y-5 rounded-lg border border-rule bg-white p-5">
        <div className="grid gap-5 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="first">First name</label>
            <input id="first" className="field" required value={form.first_name} onChange={set("first_name")} />
          </div>
          <div>
            <label className="label" htmlFor="last">Last name</label>
            <input id="last" className="field" value={form.last_name} onChange={set("last_name")} />
          </div>
        </div>

        <div className="grid gap-5 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="username">Username</label>
            <input id="username" className="field" required autoComplete="off"
                   value={form.username} onChange={set("username")} />
            <p className="mt-1 text-sm text-navy-soft">What they type to sign in. No spaces.</p>
          </div>
          <div>
            <label className="label" htmlFor="role">Role</label>
            <select id="role" className="field" value={form.role} onChange={set("role")} disabled={isSelf}>
              <option value="counsellor">Counsellor — sees only their own students</option>
              <option value="admin">Owner — sees everything, reports, team</option>
            </select>
          </div>
        </div>

        {isNew && (
          <div>
            <label className="label" htmlFor="temp">Temporary password</label>
            <div className="flex gap-2">
              <input id="temp" className="field font-mono" required value={form.password} onChange={set("password")} />
              <button type="button" className="btn-quiet shrink-0 px-3"
                      onClick={() => setForm({ ...form, password: suggestPassword() })}>New</button>
            </div>
            <p className="mt-1 text-sm text-navy-soft">They must replace it the first time they sign in.</p>
          </div>
        )}

        <div className="grid gap-5 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="email">Email</label>
            <input id="email" type="email" className="field" value={form.email} onChange={set("email")} />
            <p className="mt-1 text-sm text-navy-soft">New-student alerts go here.</p>
          </div>
          <div>
            <label className="label" htmlFor="phone">Phone</label>
            <input id="phone" type="tel" className="field" value={form.phone} onChange={set("phone")} />
          </div>
        </div>

        {form.role === "counsellor" && (
          <fieldset className="rounded-md border border-rule p-4">
            <legend className="label px-1">New students from the website</legend>
            <label className="flex items-center gap-3 text-sm text-navy">
              <input type="checkbox" className="h-4 w-4 accent-grass" checked={form.auto_assign}
                     onChange={set("auto_assign")} />
              Give this person new students automatically
            </label>
            <p className="mt-3 text-sm text-navy-soft">Countries they handle (students choosing these come to them first):</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {countries.map((c) => {
                const on = form.countries.includes(c.id);
                return (
                  <button type="button" key={c.id} onClick={() => toggleCountry(c.id)} aria-pressed={on}
                          className={`rounded-full border px-3 py-1.5 text-sm ${
                            on ? "border-grass bg-grass text-white" : "border-rule bg-white text-navy"}`}>
                    {c.name}
                  </button>
                );
              })}
            </div>
          </fieldset>
        )}

        <div>
          <label className="label" htmlFor="languages">Languages</label>
          <input id="languages" className="field" placeholder="Nepali, English" value={form.languages}
                 onChange={set("languages")} />
        </div>
        <div>
          <label className="label" htmlFor="bio">Bio (shown on the website)</label>
          <textarea id="bio" className="field" rows={2} value={form.bio} onChange={set("bio")} />
        </div>
        <label className="flex items-center gap-3 text-sm text-navy">
          <input type="checkbox" className="h-4 w-4 accent-grass" checked={form.is_public} onChange={set("is_public")} />
          Show on the public website (once they've signed in and have a bio)
        </label>

        {!resetDone && <Notice>{error}</Notice>}
        <Notice tone="ok">{saved}</Notice>
        <button className="btn-go" disabled={busy}>
          {busy ? "Saving…" : isNew ? "Add staff member" : "Save changes"}
        </button>
      </form>

      {!isNew && !isSelf && (
        <>
          <form onSubmit={resetPassword} className="mt-6 rounded-lg border border-rule bg-white p-5">
            <h2 className="text-xl">Forgotten password</h2>
            <p className="mt-1 text-sm text-navy-soft">
              Set a temporary one and tell them. They must change it when they sign in, and
              they're signed out everywhere else.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <input className="field max-w-xs font-mono" aria-label="New temporary password"
                     placeholder="Temporary password" value={newPassword}
                     onChange={(e) => setNewPassword(e.target.value)} />
              <button type="button" className="btn-quiet px-3" onClick={() => setNewPassword(suggestPassword())}>
                Suggest
              </button>
              <button className="btn-go" disabled={!newPassword}>Reset password</button>
            </div>
            {resetDone && (
              <div className="mt-4"><Notice tone="ok">
                Done. Their temporary password is <strong className="font-mono">{resetDone}</strong>
              </Notice></div>
            )}
            {resetDone === "" && error && <div className="mt-4"><Notice>{error}</Notice></div>}
          </form>

          <section className="mt-6 rounded-lg border border-rule bg-white p-5">
            <h2 className="text-xl">{person.is_active ? "Close this account" : "Reopen this account"}</h2>
            <p className="mt-1 text-sm text-navy-soft">
              {person.is_active
                ? person.open_students > 0
                  ? `They still have ${person.open_students} open students. Use "Hand over" on the Team page — it moves the students and closes the account in one step.`
                  : "They won't be able to sign in. Their name stays on every note they wrote."
                : "They'll be able to sign in again with their existing password."}
            </p>
            {(!person.is_active || person.open_students === 0) && (
              <button onClick={toggleActive}
                      className={person.is_active ? "btn-quiet mt-4 text-urgent" : "btn-go mt-4"}>
                {person.is_active ? "Close account" : "Reopen account"}
              </button>
            )}
          </section>
        </>
      )}
    </div>
  );
}
