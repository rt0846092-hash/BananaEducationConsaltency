import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { staffApi } from "../auth";

const STATUSES = [
  ["", "Every stage"], ["new", "New"], ["contacted", "Contacted"],
  ["counselling", "Counselling"], ["docs_pending", "Documents pending"],
  ["applied", "Applied"], ["offer", "Offer received"], ["visa_filed", "Visa filed"],
  ["enrolled", "Enrolled"], ["lost", "Lost"],
];

const money = (n) =>
  new Intl.NumberFormat("en-US", {
    style: "currency", currency: "USD", maximumFractionDigits: 0,
  }).format(n || 0);

export default function Reports() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [rangeError, setRangeError] = useState("");
  const [downloading, setDownloading] = useState(false);
  const [range, setRange] = useState({ from: "", to: "" });
  const [exportStatus, setExportStatus] = useState("");
  const navigate = useNavigate();

  const query = (extra = {}, r = range) => {
    const p = new URLSearchParams();
    Object.entries({ ...r, ...extra }).forEach(([k, v]) => v && p.set(k, v));
    const qs = p.toString();
    return qs ? `?${qs}` : "";
  };

  function load(r = range) {
    setRangeError("");
    staffApi
      .reports(query({}, r))
      .then(setData)
      .catch((err) => {
        if (err.message === "SESSION_EXPIRED") navigate("/staff/login");
        else if (err.status === 400) setRangeError(err.message);
        else setError(err.message);
      });
  }

  useEffect(() => load(), []); // eslint-disable-line react-hooks/exhaustive-deps

  // The CSV needs the auth header, so it can't be a plain link.
  async function download() {
    setDownloading(true);
    try {
      await staffApi.exportCsv(query({ status: exportStatus }));
    } catch (err) {
      if (err.message === "SESSION_EXPIRED") navigate("/staff/login");
      else setRangeError(err.message);
    } finally {
      setDownloading(false);
    }
  }

  if (error) {
    return (
      <div className="wrap py-20">
        <p className="text-urgent">{error}</p>
        <p className="mt-2 text-navy-soft">This page is for the office owner.</p>
      </div>
    );
  }
  if (!data) return <p className="wrap py-20 text-navy-soft">Loading…</p>;

  const widest = Math.max(...data.funnel.map((f) => f.count), 1);

  return (
    <div className="wrap py-8">
      <h1 className="text-2xl sm:text-3xl">Reports</h1>
      <p className="mt-1.5 max-w-prose text-navy-soft">
        Commission figures are what each application is expected to be worth, not money
        received.
      </p>

      <form
        onSubmit={(e) => { e.preventDefault(); load(); }}
        className="mt-6 flex flex-wrap items-end gap-3 rounded-lg border border-rule bg-white p-4"
      >
        <div>
          <label className="label" htmlFor="from">Students who enquired from</label>
          <input id="from" type="date" className="field" value={range.from}
                 onChange={(e) => setRange({ ...range, from: e.target.value })} />
        </div>
        <div>
          <label className="label" htmlFor="to">to</label>
          <input id="to" type="date" className="field" value={range.to}
                 onChange={(e) => setRange({ ...range, to: e.target.value })} />
        </div>
        <button className="btn-go">Show</button>
        {(range.from || range.to) && (
          <button type="button" className="btn-quiet"
                  onClick={() => { const all = { from: "", to: "" }; setRange(all); load(all); }}>
            All time
          </button>
        )}
        {rangeError && <p className="w-full text-sm text-urgent">{rangeError}</p>}
      </form>

      <div className="mt-6 grid gap-3 sm:grid-cols-2">
        <div className="rounded-lg border border-rule bg-white p-5">
          <div className="font-display text-3xl font-semibold text-navy-deep">
            {money(data.pipeline_value)}
          </div>
          <div className="mt-1 text-sm text-navy-soft">
            In flight — applications submitted but not yet enrolled
          </div>
        </div>
        <div className="rounded-lg border border-grass/30 bg-grass-pale p-5">
          <div className="font-display text-3xl font-semibold text-grass-dark">
            {money(data.won_value)}
          </div>
          <div className="mt-1 text-sm text-navy">Earned — students who enrolled</div>
        </div>
      </div>

      <section className="mt-8">
        <h2 className="text-xl">Where students drop out</h2>
        <p className="mt-1 max-w-prose text-sm text-navy-soft">
          A big fall between the first two rows means marketing is bringing the wrong
          people. A fall between the last two means the visa and documents stage needs
          help.
        </p>
        <div className="mt-5 space-y-3">
          {data.funnel.map((step) => (
            <div key={step.label} className="flex items-center gap-4">
              <div className="w-40 shrink-0 text-sm text-navy">{step.label}</div>
              <div className="h-7 flex-1 rounded bg-paper">
                <div
                  className="flex h-7 items-center rounded bg-navy px-3 text-sm text-white"
                  style={{ width: `${Math.max((step.count / widest) * 100, 8)}%` }}
                >
                  {step.count}
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {data.by_stage.length > 0 && (
        <section className="mt-10">
          <h2 className="text-xl">Applications by stage</h2>
          <div className="mt-4 overflow-hidden rounded-lg border border-rule bg-white">
            <table className="w-full text-left">
              <thead className="border-b border-rule text-sm text-navy-soft">
                <tr>
                  <th className="p-4 font-medium">Stage</th>
                  <th className="p-4 font-medium">Applications</th>
                  <th className="p-4 font-medium">Expected commission</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-rule">
                {data.by_stage.map((row) => (
                  <tr key={row.status}>
                    <td className="p-4 text-navy">{row.label}</td>
                    <td className="p-4 text-navy">{row.count}</td>
                    <td className="p-4 text-navy-soft">{money(row.value)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {data.by_source?.length > 0 && (
        <section className="mt-10">
          <h2 className="text-xl">Which sources produce students</h2>
          <p className="mt-1 max-w-prose text-sm text-navy-soft">
            Each QR code and each way a walk-in heard about you has its own tag. Enrolments
            matter more than enquiries.
          </p>
          <div className="mt-4 overflow-x-auto rounded-lg border border-rule bg-white">
            <table className="w-full text-left">
              <thead className="border-b border-rule text-sm text-navy-soft">
                <tr>
                  <th className="p-4 font-medium">Source</th>
                  <th className="p-4 font-medium">Enquiries</th>
                  <th className="p-4 font-medium">Enrolled</th>
                  <th className="p-4 font-medium">Rate</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-rule">
                {data.by_source.map((r) => (
                  <tr key={r.source}>
                    <td className="p-4 text-navy">{r.source}</td>
                    <td className="p-4 text-navy">{r.count}</td>
                    <td className="p-4 text-navy">{r.enrolled}</td>
                    <td className="p-4 text-navy-soft">
                      {r.count ? `${Math.round((r.enrolled / r.count) * 100)}%` : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <section className="mt-10 rounded-lg border border-rule bg-white p-5">
        <h2 className="text-xl">Export the student list</h2>
        <p className="mt-1.5 max-w-prose text-sm leading-relaxed text-navy-soft">
          Only you can do this, and every export is recorded with the date and how many
          rows left the system. Counsellors get 403 from this endpoint even if they call
          it directly.
        </p>
        <div className="mt-4 flex flex-wrap items-end gap-3">
          <div>
            <label className="label" htmlFor="exstatus">Stage</label>
            <select id="exstatus" className="field" value={exportStatus}
                    onChange={(e) => setExportStatus(e.target.value)}>
              {STATUSES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </div>
          <button onClick={download} className="btn-quiet" disabled={downloading}>
            {downloading ? "Preparing…" : "Download CSV"}
          </button>
        </div>
        <p className="mt-2 text-sm text-navy-soft">
          Uses the date range above. Opens correctly in Excel, including Nepali and Korean names.
        </p>
      </section>
    </div>
  );
}
