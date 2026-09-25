import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { staffApi } from "../auth";
/* global __DEMO__ */
import Logo from "../components/Logo";

export default function StaffLogin() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await staffApi.login(username, password);
      // A brand new account has a password the owner chose. Send them straight
      // to setting their own — the server blocks everything else anyway.
      const me = await staffApi.me();
      navigate(me.must_change_password ? "/staff/password" : "/staff");
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <div className="wrap max-w-sm py-20">
      <Logo className="h-12 w-12" />
      <h1 className="mt-6 text-2xl">Staff sign in</h1>
      <p className="mt-1.5 text-sm text-navy-soft">
        For counsellors and office staff.
      </p>

      <form onSubmit={submit} className="mt-8 space-y-4">
        <div>
          <label className="label" htmlFor="u">Username</label>
          <input
            id="u" className="field" autoComplete="username" required
            value={username} onChange={(e) => setUsername(e.target.value)}
          />
        </div>
        <div>
          <label className="label" htmlFor="p">Password</label>
          <input
            id="p" className="field" type="password" autoComplete="current-password" required
            value={password} onChange={(e) => setPassword(e.target.value)}
          />
        </div>

        {error && (
          <p className="rounded-md border border-urgent/30 bg-urgent/5 px-4 py-3 text-sm text-urgent">
            {error}
          </p>
        )}

        <button className="btn-go w-full" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>

      {/* Only with VITE_DEMO_MODE=true. On a real client's site, publishing
          the logins would hand the student list to anyone who looks. */}
      {__DEMO__ && (
      <div className="mt-8 rounded-md border border-rule bg-white p-4 text-sm text-navy-soft">
        <p className="font-medium text-navy">Demo accounts</p>
        <p className="mt-1.5">
          <code>admin</code> sees every student and the reports.
          <br />
          <code>sarita</code> or <code>mingma</code> see only their own.
          <br />
          Password for all three: <code>banana123</code>
        </p>
      </div>
      )}
    </div>
  );
}