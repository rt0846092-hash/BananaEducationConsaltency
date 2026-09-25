import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { setToken, staffApi } from "../auth";

export default function ChangePassword() {
  const [me, setMe] = useState(null);
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [errors, setErrors] = useState([]);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    staffApi.me().then(setMe).catch(() => navigate("/staff/login"));
  }, [navigate]);

  async function submit(e) {
    e.preventDefault();
    if (next !== confirm) {
      setErrors(["The two new passwords don't match."]);
      return;
    }
    setBusy(true);
    setErrors([]);
    try {
      // Changing the password signs out every other device. The server
      // sends a fresh token for this one so you stay signed in here.
      const res = await staffApi.changePassword({ current_password: current, new_password: next });
      if (res?.access) setToken(res.access);
      setDone(true);
      setTimeout(() => navigate("/staff"), 1200);
    } catch (err) {
      setErrors([err.message]);
      setBusy(false);
    }
  }

  const forced = me?.must_change_password;

  if (done) {
    return (
      <div className="wrap max-w-sm py-20 text-center">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-grass-pale">
          <span className="text-2xl text-grass">✓</span>
        </div>
        <h1 className="mt-6 text-2xl">Password changed</h1>
        <p className="mt-2 text-navy-soft">Taking you to your students…</p>
      </div>
    );
  }

  return (
    <div className="wrap max-w-sm py-16">
      <h1 className="text-2xl">
        {forced ? "Choose your own password" : "Change your password"}
      </h1>

      {forced ? (
        <p className="mt-2 leading-relaxed text-navy-soft">
          The password you signed in with was set by the office owner, so two people know
          it. Pick one only you know — after this, anything recorded under your name can
          only have come from you.
        </p>
      ) : (
        <p className="mt-2 text-navy-soft">You'll stay signed in on this device.</p>
      )}

      <form onSubmit={submit} className="mt-8 space-y-4">
        <div>
          <label className="label" htmlFor="cur">
            {forced ? "The password you were given" : "Current password"}
          </label>
          <input
            id="cur" className="field" type="password" required autoComplete="current-password"
            value={current} onChange={(e) => setCurrent(e.target.value)}
          />
        </div>
        <div>
          <label className="label" htmlFor="new">New password</label>
          <input
            id="new" className="field" type="password" required autoComplete="new-password"
            value={next} onChange={(e) => setNext(e.target.value)}
          />
          <p className="mt-1.5 text-sm text-navy-soft">
            At least eight characters, and not something obvious like your name or the
            office name.
          </p>
        </div>
        <div>
          <label className="label" htmlFor="conf">New password again</label>
          <input
            id="conf" className="field" type="password" required autoComplete="new-password"
            value={confirm} onChange={(e) => setConfirm(e.target.value)}
          />
        </div>

        {errors.length > 0 && (
          <div className="rounded-md border border-urgent/30 bg-urgent/5 px-4 py-3 text-sm text-urgent">
            {errors.map((msg) => <p key={msg}>{msg}</p>)}
          </div>
        )}

        <button className="btn-go w-full" disabled={busy}>
          {busy ? "Saving…" : "Save password"}
        </button>
      </form>
    </div>
  );
}