import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { staffApi } from "../auth";

function Handover({ person, team, onDone, onCancel }) {
  const others = team.filter((p) => p.id !== person.id);
  const [toUser, setToUser] = useState(others[0]?.id || "");
  const [reason, setReason] = useState("");
  const [closeAccount, setCloseAccount] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      onDone(
        await staffApi.handover({
          from_user: person.id,
          to_user: Number(toUser),
          reason,
          deactivate: closeAccount,
        })
      );
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="border-t border-rule bg-paper p-5">
      <h3 className="text-base">Hand over {person.name}'s students</h3>
      <p className="mt-1 text-sm leading-relaxed text-navy-soft">
        Moves their {person.live} open {person.live === 1 ? "student" : "students"} to
        somebody else and marks each one for a call today. Closed cases stay where they
        are, so the record of who handled them survives.
      </p>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <div>
          <label className="label" htmlFor="to">Who receives them</label>
          <select id="to" className="field" value={toUser} onChange={(e) => setToUser(e.target.value)}>
            {others.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} — {p.live} open now
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="label" htmlFor="reason">Reason</label>
          <input
            id="reason" className="field" placeholder="Resigned, last day Friday"
            value={reason} onChange={(e) => setReason(e.target.value)}
          />
        </div>
      </div>

      <label className="mt-4 flex gap-3 rounded-md border border-rule bg-white p-4">
        <input
          type="checkbox" className="mt-1 h-4 w-4 accent-grass"
          checked={closeAccount} onChange={(e) => setCloseAccount(e.target.checked)}
        />
        <span className="text-sm leading-relaxed text-navy">
          Close {person.name}'s account. They can't sign in again, but their name stays on
          every call note they wrote — the account is switched off, never deleted.
        </span>
      </label>

      {error && (
        <p className="mt-4 rounded-md border border-urgent/30 bg-urgent/5 px-4 py-3 text-sm text-urgent">
          {error}
        </p>
      )}

      <div className="mt-4 flex gap-3">
        <button className="btn-go" disabled={busy || !toUser}>
          {busy ? "Moving…" : `Move ${person.live} and confirm`}
        </button>
        <button type="button" onClick={onCancel} className="btn-quiet">Cancel</button>
      </div>
    </form>
  );
}

export default function Team() {
  const [team, setTeam] = useState([]);
  const [closed, setClosed] = useState([]);
  const [openFor, setOpenFor] = useState(null);
  const [done, setDone] = useState(null);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const load = () =>
    Promise.all([staffApi.team(), staffApi.staffList()])
      .then(([t, all]) => {
        setTeam(t);
        setClosed(all.filter((p) => !p.is_active));
      })
      .catch((err) => {
        if (err.message === "SESSION_EXPIRED") navigate("/staff/login");
        else setError(err.message);
      });

  useEffect(() => {
    load();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (error) {
    return (
      <div className="wrap py-20">
        <p className="text-urgent">{error}</p>
        <p className="mt-2 text-navy-soft">This page is for the office owner.</p>
      </div>
    );
  }

  return (
    <div className="wrap py-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <h1 className="text-2xl sm:text-3xl">Your team</h1>
        <Link to="/staff/team/new" className="btn-go px-4 py-2 text-sm">+ Add staff</Link>
      </div>
      <p className="mt-1.5 max-w-prose text-navy-soft">
        Who is carrying what, and who is falling behind. The overdue column is the one to
        watch daily.
      </p>

      {done && (
        <div className="mt-6 rounded-lg border border-grass/30 bg-grass-pale p-4">
          <p className="text-navy">
            Moved {done.moved} {done.moved === 1 ? "student" : "students"} to {done.to}
            {done.deactivated && ", and closed the old account"}. Every move is in the
            handover log.
          </p>
        </div>
      )}

      <div className="mt-6 overflow-hidden rounded-lg border border-rule bg-white">
        <table className="w-full text-left">
          <thead className="border-b border-rule text-sm text-navy-soft">
            <tr>
              <th className="p-4 font-medium">Name</th>
              <th className="p-4 font-medium">Open</th>
              <th className="p-4 font-medium">Overdue</th>
              <th className="p-4 font-medium">Enrolled</th>
              <th className="p-4" />
            </tr>
          </thead>
          <tbody className="divide-y divide-rule">
            {team.map((p) => (
              <tr key={p.id} className="align-middle">
                <td className="p-4">
                  <div className="font-medium text-navy-deep">{p.name}</div>
                  <div className="text-sm text-navy-soft">
                    {p.role === "admin" ? "Owner" : "Counsellor"}
                    {p.languages && ` · ${p.languages}`}
                  </div>
                  {p.role !== "admin" && (
                    <div className="mt-0.5 text-xs text-navy-soft">
                      {p.auto_assign
                        ? `Gets new website students${p.countries.length ? ` · ${p.countries.join(", ")}` : " · any country"}`
                        : "Not receiving new website students"}
                    </div>
                  )}
                </td>
                <td className="p-4 text-navy">{p.live}</td>
                <td className="p-4">
                  <span className={p.overdue > 0 ? "font-medium text-urgent" : "text-navy-soft"}>
                    {p.overdue}
                  </span>
                </td>
                <td className="p-4 text-navy">{p.enrolled}</td>
                <td className="p-4 text-right">
                  <Link to={`/staff/team/${p.id}`} className="mr-4 text-sm font-medium text-navy hover:underline">
                    Edit
                  </Link>
                  {p.live > 0 && (
                    <button
                      onClick={() => {
                        setDone(null);
                        setOpenFor(openFor === p.id ? null : p.id);
                      }}
                      className="text-sm font-medium text-grass hover:underline"
                    >
                      Hand over
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {openFor && (
          <Handover
            person={team.find((p) => p.id === openFor)}
            team={team}
            onCancel={() => setOpenFor(null)}
            onDone={(result) => {
              setOpenFor(null);
              setDone(result);
              load();
            }}
          />
        )}
      </div>

      <p className="mt-5 max-w-prose text-sm leading-relaxed text-navy-soft">
        New website students go to the counsellor who handles their chosen country and has
        the fewest open students. Change someone's countries, or reset a forgotten password,
        with <strong>Edit</strong>.
      </p>

      {closed.length > 0 && (
        <section className="mt-10">
          <h2 className="text-xl">Closed accounts</h2>
          <ul className="mt-3 divide-y divide-rule rounded-lg border border-rule bg-white">
            {closed.map((p) => (
              <li key={p.id} className="flex items-center justify-between gap-3 p-4">
                <span className="text-navy-soft">
                  {[p.first_name, p.last_name].filter(Boolean).join(" ") || p.username}
                  <span className="text-sm"> · {p.username}</span>
                </span>
                <Link to={`/staff/team/${p.id}`} className="text-sm font-medium text-navy hover:underline">
                  View / reopen
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
