import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { staffApi } from "../auth";

/**
 * Everything a person can change about their own account, without the
 * Django admin. Role and active status stay with the owner.
 */
export default function Account() {
  const navigate = useNavigate();
  const [me, setMe] = useState(null);
  const [form, setForm] = useState(null);
  const [currentPassword, setCurrentPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    staffApi.me().then((u) => {
      if (u.must_change_password) return navigate("/staff/password");
      setMe(u);
      setForm({
        username: u.username, first_name: u.first_name, last_name: u.last_name,
        email: u.email, phone: u.phone, languages: u.languages, bio: u.bio,
        is_public: u.is_public,
      });
    }).catch(() => navigate("/staff/login"));
  }, [navigate]);

  if (!form) return <p className="wrap py-20 text-navy-soft">Loading…</p>;

  const set = (k) => (e) => {
    setSaved(false);
    setForm({ ...form, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });
  };
  const usernameChanged = form.username.trim() !== me.username;

  async function save(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setSaved(false);
    try {
      const data = { ...form, username: form.username.trim() };
      if (usernameChanged) data.current_password = currentPassword;
      const updated = await staffApi.updateMe(data);
      setMe(updated);
      setCurrentPassword("");
      setSaved(true);
    } catch (err) {
      if (err.message === "SESSION_EXPIRED") return navigate("/staff/login");
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="wrap max-w-2xl py-8">
      <Link to="/staff" className="text-sm text-navy-soft hover:text-grass">Back to the list</Link>
      <h1 className="mt-4 text-2xl sm:text-3xl">My account</h1>
      <p className="mt-1.5 text-navy-soft">
        {me.is_admin ? "Owner" : "Counsellor"} · signed in as <strong>{me.username}</strong>
      </p>

      <section className="mt-8 rounded-lg border border-rule bg-white p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-xl">Password</h2>
            <p className="mt-1 text-sm text-navy-soft">
              Changing it signs you out on every other phone and computer.
            </p>
          </div>
          <Link to="/staff/password" className="btn-quiet">Change password</Link>
        </div>
      </section>

      <form onSubmit={save} className="mt-6 space-y-5 rounded-lg border border-rule bg-white p-5">
        <h2 className="text-xl">Sign-in name and profile</h2>

        <div>
          <label className="label" htmlFor="username">Username</label>
          <input id="username" className="field" required autoComplete="username"
                 value={form.username} onChange={set("username")} />
          <p className="mt-1.5 text-sm text-navy-soft">
            What you type to sign in. Letters, numbers and @ . + - _ only, no spaces.
          </p>
        </div>

        {usernameChanged && (
          <div className="rounded-md border border-urgent/30 bg-urgent/5 p-4">
            <label className="label" htmlFor="curpw">Your current password</label>
            <input id="curpw" type="password" className="field" required
                   autoComplete="current-password"
                   value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} />
            <p className="mt-1.5 text-sm text-navy">
              Needed to change your username. Afterwards you sign in as{" "}
              <strong>{form.username.trim() || "…"}</strong>.
            </p>
          </div>
        )}

        <div className="grid gap-5 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="first">First name</label>
            <input id="first" className="field" value={form.first_name} onChange={set("first_name")} />
          </div>
          <div>
            <label className="label" htmlFor="last">Last name</label>
            <input id="last" className="field" value={form.last_name} onChange={set("last_name")} />
          </div>
        </div>

        <div className="grid gap-5 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="email">Email</label>
            <input id="email" type="email" className="field" value={form.email} onChange={set("email")} />
            <p className="mt-1.5 text-sm text-navy-soft">New-student alerts go here.</p>
          </div>
          <div>
            <label className="label" htmlFor="phone">Phone</label>
            <input id="phone" type="tel" className="field" value={form.phone} onChange={set("phone")} />
          </div>
        </div>

        <div>
          <label className="label" htmlFor="languages">Languages you speak</label>
          <input id="languages" className="field" placeholder="Nepali, English, Hindi"
                 value={form.languages} onChange={set("languages")} />
        </div>

        <div>
          <label className="label" htmlFor="bio">Short bio</label>
          <textarea id="bio" className="field" rows={3}
                    placeholder="e.g. Handles Australia and the UK. Former visa documentation officer."
                    value={form.bio} onChange={set("bio")} />
        </div>

        <label className="flex gap-3 text-sm leading-relaxed text-navy">
          <input type="checkbox" className="mt-1 h-4 w-4 accent-grass"
                 checked={form.is_public} onChange={set("is_public")} />
          <span>
            Show me on the public website under "The people you'll be talking to".
            You appear once you also have a bio.
          </span>
        </label>

        {error && (
          <p className="rounded-md border border-urgent/30 bg-urgent/5 px-4 py-3 text-sm text-urgent">{error}</p>
        )}
        {saved && (
          <p className="rounded-md border border-grass/30 bg-grass-pale px-4 py-3 text-sm text-grass-dark">
            Saved.{usernameChanged ? "" : ` You sign in as ${me.username}.`}
          </p>
        )}

        <button className="btn-go" disabled={busy}>{busy ? "Saving…" : "Save changes"}</button>
      </form>
    </div>
  );
}
