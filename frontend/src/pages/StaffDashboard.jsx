import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { staffApi } from "../auth";
import StatusChip from "../components/StatusChip";

const TABS = [
  ["overdue", "Needs a call", "?overdue=true"],
  ["new", "New", "?status=new"],
  ["unassigned", "Unassigned", "?unassigned=true", "admin"],
  ["all", "Everyone", ""],
];

function Stat({ label, value, urgent }) {
  return (
    <div className="rounded-lg border border-rule bg-white p-4">
      <div
        className={`font-display text-3xl font-semibold ${
          urgent && value > 0 ? "text-urgent" : "text-navy-deep"
        }`}
      >
        {value}
      </div>
      <div className="mt-1 text-sm text-navy-soft">{label}</div>
    </div>
  );
}

export default function StaffDashboard() {
  const [me, setMe] = useState(null);
  const [stats, setStats] = useState(null);
  const [leads, setLeads] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [moreLoading, setMoreLoading] = useState(false);
  const [tab, setTab] = useState("overdue");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    Promise.all([staffApi.me(), staffApi.dashboard()])
      .then(([u, d]) => {
        setMe(u);
        setStats(d);
      })
      .catch((err) => {
        if (err.message === "SESSION_EXPIRED") navigate("/staff/login");
        if (err.message === "PASSWORD_CHANGE_REQUIRED") navigate("/staff/password");
      });
  }, [navigate]);

  const buildQuery = (pageNo) => {
    const params = new URLSearchParams(TABS.find((t) => t[0] === tab)[2]);
    if (search) params.set("search", search);
    if (pageNo > 1) params.set("page", pageNo);
    const qs = params.toString();
    return qs ? `?${qs}` : "";
  };

  // The API pages at 25. Without this the office silently stopped showing
  // anyone past the 25th student.
  function showMore() {
    const next = page + 1;
    setMoreLoading(true);
    staffApi
      .leads(buildQuery(next))
      .then((d) => {
        setLeads((prev) => [...prev, ...(d.results || [])]);
        setPage(next);
      })
      .catch(() => {})
      .finally(() => setMoreLoading(false));
  }

  useEffect(() => {
    setLoading(true);
    setPage(1);
    const query = buildQuery(1);

    // Wait for the person to stop typing before asking the server. Without
    // this every keystroke fires a request and the results arrive out of order.
    const timer = setTimeout(() => {
      staffApi
        .leads(query)
        .then((d) => {
          setLeads(d.results || d);
          setTotal(d.count ?? (d.results || d).length);
        })
        .catch((err) => {
          if (err.message === "SESSION_EXPIRED") navigate("/staff/login");
        })
        .finally(() => setLoading(false));
    }, 250);

    return () => clearTimeout(timer);
  }, [tab, search, navigate]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="wrap py-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <h1 className="text-2xl sm:text-3xl">
          {me?.is_admin ? "Office overview" : `Your students, ${me?.name || ""}`}
        </h1>
        <Link to="/staff/new" className="btn-go px-4 py-2 text-sm">+ Add student</Link>
      </div>
      <p className="mt-1.5 text-navy-soft">
        {me?.is_admin
          ? "Every student in the office."
          : "Only the students assigned to you."}
      </p>

      {/* The owner gets the business picture. A counsellor doesn't need it and
          would only have to scroll past it to reach today's call list. */}
      {me?.is_admin && stats && (
        <>
          <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <Stat label="Not called in 48 hours" value={stats.uncontacted} urgent />
            <Stat label="Waiting to be assigned" value={stats.unassigned} urgent />
            <Stat label="New this week" value={stats.new_this_week} />
            <Stat label="Follow up today" value={stats.follow_up_today} />
            <Stat label="Enrolled this year" value={stats.enrolled_this_year} />
          </div>

          {stats.by_source?.length > 0 && (
            <div className="mt-6 rounded-lg border border-rule bg-white p-5">
              <h2 className="text-base">Where this week's students came from</h2>
              <div className="mt-4 space-y-2.5">
                {stats.by_source.map((row) => {
                  const top = Math.max(...stats.by_source.map((r) => r.count));
                  return (
                    <div key={row.source || "none"} className="flex items-center gap-3">
                      <div className="w-32 shrink-0 text-sm text-navy">
                        {row.source || "unknown"}
                      </div>
                      <div className="h-2.5 flex-1 rounded-full bg-paper">
                        <div
                          className="h-2.5 rounded-full bg-grass"
                          style={{ width: `${(row.count / top) * 100}%` }}
                        />
                      </div>
                      <div className="w-8 text-right text-sm text-navy-soft">{row.count}</div>
                    </div>
                  );
                })}
              </div>
              <p className="mt-4 text-sm text-navy-soft">
                Each printed QR code carries its own tag, so you can tell which poster,
                branch or fair is worth repeating.
              </p>
            </div>
          )}
        </>
      )}

      <div className="mt-8 flex flex-wrap items-center gap-3">
        <div className="flex gap-1.5">
          {TABS.filter((t) => !t[3] || me?.is_admin).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`rounded-full px-4 py-2 text-sm transition-colors ${
                tab === key
                  ? "bg-navy-deep text-white"
                  : "border border-rule bg-white text-navy hover:border-navy-soft"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <input
          className="field ml-auto w-full sm:w-64"
          placeholder="Search name or phone"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <div className="mt-5 overflow-hidden rounded-lg border border-rule bg-white">
        {loading ? (
          <p className="p-8 text-center text-navy-soft">Loading…</p>
        ) : leads.length === 0 ? (
          <p className="p-8 text-center text-navy-soft">
            {tab === "overdue"
              ? "Nobody is waiting on a call. That's the goal."
              : tab === "unassigned"
              ? "Every student has a counsellor."
              : "Nothing here yet."}
          </p>
        ) : (
          <ul className="divide-y divide-rule">
            {leads.map((lead) => (
              <li key={lead.id}>
                <Link
                  to={`/staff/leads/${lead.id}`}
                  className="flex flex-wrap items-center gap-x-4 gap-y-1 p-4 hover:bg-paper"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium text-navy-deep">{lead.full_name}</span>
                      {lead.is_overdue && (
                        <span className="rounded bg-urgent/10 px-2 py-0.5 text-xs font-medium text-urgent">
                          Needs a call
                        </span>
                      )}
                    </div>
                    <div className="mt-0.5 text-sm text-navy-soft">
                      {lead.phone}
                      {lead.countries.length > 0 && ` · ${lead.countries.join(", ")}`}
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    {me?.is_admin && (
                      <span className="text-sm text-navy-soft">
                        {lead.assigned_to_name || "Unassigned"}
                      </span>
                    )}
                    <StatusChip status={lead.status} label={lead.status_display} />
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>

      {!loading && leads.length < total && (
        <div className="mt-4 flex items-center justify-between gap-3 text-sm text-navy-soft">
          <span>Showing {leads.length} of {total}</span>
          <button onClick={showMore} disabled={moreLoading} className="btn-quiet">
            {moreLoading ? "Loading…" : "Show more"}
          </button>
        </div>
      )}
    </div>
  );
}
