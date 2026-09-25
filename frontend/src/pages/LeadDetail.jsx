import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { staffApi } from "../auth";
import { DEFAULT_COUNTRY_CODE } from "../config";
import StatusChip from "../components/StatusChip";

const STATUSES = [
  ["new", "New"], ["contacted", "Contacted"], ["counselling", "Counselling"],
  ["docs_pending", "Documents pending"], ["applied", "Applied"],
  ["offer", "Offer received"], ["visa_filed", "Visa filed"],
  ["enrolled", "Enrolled"], ["lost", "Lost"],
];

const APP_STATUSES = [
  ["draft", "Draft"], ["submitted", "Submitted"],
  ["offer_conditional", "Conditional offer"], ["offer_unconditional", "Unconditional offer"],
  ["rejected", "Rejected by university"], ["visa_filed", "Visa filed"],
  ["visa_approved", "Visa approved"], ["visa_refused", "Visa refused"],
  ["enrolled", "Enrolled"], ["withdrawn", "Withdrawn"],
];

const DOC_TYPES = [
  ["passport", "Passport"], ["transcript", "Academic transcript"],
  ["certificate", "Certificate"], ["test_score", "Test score report"],
  ["bank_statement", "Bank statement"], ["sponsor", "Sponsor documents"],
  ["sop", "Statement of purpose"], ["other", "Other"],
];

// What almost every file needs. Ticked off as documents arrive.
const CHECKLIST = ["passport", "transcript", "test_score", "bank_statement", "sop"];

const shortDate = (d) =>
  new Date(d).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
const dateTime = (d) =>
  new Date(d).toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
const money = (n) =>
  n == null || n === "" ? "" : new Intl.NumberFormat("en-US", {
    style: "currency", currency: "USD", maximumFractionDigits: 0,
  }).format(n);
const fileSize = (b) =>
  b == null ? "" : b > 1024 * 1024 ? `${(b / 1024 / 1024).toFixed(1)} MB` : `${Math.ceil(b / 1024)} KB`;

/** wa.me needs the full international number with no + or spaces. */
function whatsappLink(phone) {
  let digits = phone.replace(/\D/g, "");
  if (digits.startsWith("00")) digits = digits.slice(2);
  if (digits.length === 10 && !phone.trim().startsWith("+")) digits = DEFAULT_COUNTRY_CODE + digits;
  return `https://wa.me/${digits}`;
}

function Fact({ label, value }) {
  if (value === null || value === undefined || value === "" || value === false) return null;
  return (
    <div>
      <dt className="text-sm text-navy-soft">{label}</dt>
      <dd className="mt-0.5 text-navy">{value}</dd>
    </div>
  );
}

function SectionError({ message }) {
  if (!message) return null;
  return (
    <p className="mt-3 rounded-md border border-urgent/30 bg-urgent/5 px-4 py-3 text-sm text-urgent">
      {message}
    </p>
  );
}

function Applications({ lead, me, onChange, onError: raise }) {
  const [err, setErr] = useState("");
  // Show problems next to the form they came from, not at the top of the page.
  const onError = (e) => (e.message === "SESSION_EXPIRED" ? raise(e) : setErr(e.message));
  const [unis, setUnis] = useState([]);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const blank = { university: "", course: "", intake: lead.target_intake || "", deadline: "",
                  status: "draft", commission_expected: "" };
  const [form, setForm] = useState(blank);

  useEffect(() => {
    if (open && !unis.length) staffApi.universities().then(setUnis).catch(onError);
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

  const courses = unis.find((u) => String(u.id) === String(form.university))?.courses || [];
  const byCountry = unis.reduce((acc, u) => {
    (acc[u.country_name] ||= []).push(u);
    return acc;
  }, {});

  async function add(e) {
    e.preventDefault();
    setBusy(true);
    const data = Object.fromEntries(Object.entries(form).filter(([, v]) => v !== ""));
    setErr("");
    try {
      await staffApi.addApplication(lead.id, data);
      setForm(blank);
      setOpen(false);
      onChange();
    } catch (err) {
      onError(err);
    } finally {
      setBusy(false);
    }
  }

  async function update(app, data) {
    setErr("");
    try {
      await staffApi.updateApplication(app.id, data);
      onChange();
    } catch (err) {
      onError(err);
    }
  }

  return (
    <section className="mt-10">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-xl">Applications</h2>
        <button className="btn-quiet px-4 py-2 text-sm" onClick={() => setOpen(!open)}>
          {open ? "Cancel" : "+ Add application"}
        </button>
      </div>
      <SectionError message={err} />

      {open && (
        <form onSubmit={add} className="mt-4 grid gap-4 rounded-lg border border-rule bg-white p-5 sm:grid-cols-2">
          <div className="sm:col-span-2">
            <label className="label" htmlFor="uni">University</label>
            <select id="uni" className="field" required value={form.university}
                    onChange={(e) => setForm({ ...form, university: e.target.value, course: "" })}>
              <option value="">Choose a university</option>
              {Object.entries(byCountry).map(([country, list]) => (
                <optgroup key={country} label={country}>
                  {list.map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}
                </optgroup>
              ))}
            </select>
          </div>
          <div className="sm:col-span-2">
            <label className="label" htmlFor="course">Course</label>
            <select id="course" className="field" value={form.course} disabled={!courses.length}
                    onChange={(e) => setForm({ ...form, course: e.target.value })}>
              <option value="">{courses.length ? "Choose a course" : "No courses listed"}</option>
              {courses.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <div>
            <label className="label" htmlFor="app-intake">Intake</label>
            <input id="app-intake" className="field" placeholder="Sep 2027" value={form.intake}
                   onChange={(e) => setForm({ ...form, intake: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="app-deadline">Deadline</label>
            <input id="app-deadline" type="date" className="field" value={form.deadline}
                   onChange={(e) => setForm({ ...form, deadline: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="app-status">Stage</label>
            <select id="app-status" className="field" value={form.status}
                    onChange={(e) => setForm({ ...form, status: e.target.value })}>
              {APP_STATUSES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </div>
          {/* Commission is the owner's business figure; the server ignores it from counsellors. */}
          {me?.is_admin && (
            <div>
              <label className="label" htmlFor="app-commission">Expected commission (USD)</label>
              <input id="app-commission" type="number" min="0" step="1" className="field"
                     value={form.commission_expected}
                     onChange={(e) => setForm({ ...form, commission_expected: e.target.value })} />
            </div>
          )}
          <div className="sm:col-span-2">
            <button className="btn-go" disabled={busy}>{busy ? "Saving…" : "Save application"}</button>
          </div>
        </form>
      )}

      {lead.applications.length === 0 && !open ? (
        <p className="mt-3 text-navy-soft">No applications yet.</p>
      ) : (
        <ul className="mt-4 divide-y divide-rule rounded-lg border border-rule bg-white">
          {lead.applications.map((a) => {
            const soon = a.deadline && new Date(a.deadline) - new Date() < 14 * 864e5
              && !["enrolled", "withdrawn", "rejected"].includes(a.status);
            return (
              <li key={a.id} className="flex flex-wrap items-center justify-between gap-3 p-4">
                <div className="min-w-0">
                  <div className="text-navy-deep">{a.university_name}</div>
                  <div className="text-sm text-navy-soft">
                    {[a.course_name, a.country_name, a.intake].filter(Boolean).join(" · ")}
                    {a.deadline && (
                      <span className={soon ? " font-medium text-urgent" : ""}>
                        {" · "}deadline {shortDate(a.deadline)}
                      </span>
                    )}
                    {me?.is_admin && a.commission_expected && ` · ${money(a.commission_expected)}`}
                  </div>
                </div>
                <select className="field w-auto py-2 text-sm" value={a.status}
                        aria-label={`Stage for ${a.university_name}`}
                        onChange={(e) => update(a, { status: e.target.value })}>
                  {APP_STATUSES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

function Documents({ lead, me, onChange, onError: raise }) {
  const [err, setErr] = useState("");
  const onError = (e) => (e.message === "SESSION_EXPIRED" ? raise(e) : setErr(e.message));
  const [docType, setDocType] = useState("passport");
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [inputKey, setInputKey] = useState(0);
  const have = new Set(lead.documents.map((d) => d.doc_type));

  async function upload(e) {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    const fd = new FormData();
    fd.append("doc_type", docType);
    fd.append("file", file);
    setErr("");
    try {
      await staffApi.uploadDocument(lead.id, fd);
      setFile(null);
      setInputKey((k) => k + 1);
      onChange();
    } catch (err) {
      onError(err);
    } finally {
      setBusy(false);
    }
  }

  async function act(fn) {
    setErr("");
    try {
      await fn();
      onChange();
    } catch (err) {
      onError(err);
    }
  }

  return (
    <section className="mt-10">
      <h2 className="text-xl">Documents</h2>

      {me && !me.documents_persistent && (
        <p className="mt-3 rounded-md border border-urgent/30 bg-urgent/5 p-3 text-sm text-urgent">
          File storage isn't set up yet, so uploads will be lost the next time the site is
          deployed. Ask whoever runs the site to add cloud storage (see the README).
        </p>
      )}

      <ul className="mt-4 flex flex-wrap gap-2" aria-label="Checklist">
        {CHECKLIST.map((type) => {
          const docs = lead.documents.filter((d) => d.doc_type === type);
          const verified = docs.some((d) => d.is_verified);
          const label = DOC_TYPES.find(([v]) => v === type)[1];
          return (
            <li key={type} className={`rounded-full border px-3 py-1 text-sm ${
              verified ? "border-grass bg-grass text-white"
                : have.has(type) ? "border-grass/40 bg-grass-pale text-grass-dark"
                : "border-rule bg-white text-navy-soft"}`}>
              {verified ? "✓ " : have.has(type) ? "• " : "○ "}{label}
              <span className="sr-only">
                {verified ? " verified" : have.has(type) ? " received, not verified" : " missing"}
              </span>
            </li>
          );
        })}
      </ul>

      <form onSubmit={upload} className="mt-4 flex flex-wrap items-end gap-3 rounded-lg border border-rule bg-white p-4">
        <div>
          <label className="label" htmlFor="doctype">Type</label>
          <select id="doctype" className="field" value={docType} onChange={(e) => setDocType(e.target.value)}>
            {DOC_TYPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </div>
        <div className="min-w-0 flex-1">
          <label className="label" htmlFor="docfile">File (PDF, photo or Word)</label>
          <input key={inputKey} id="docfile" type="file" className="field py-2"
                 accept=".pdf,.jpg,.jpeg,.png,.webp,.doc,.docx"
                 onChange={(e) => setFile(e.target.files[0] || null)} />
        </div>
        <button className="btn-go" disabled={busy || !file}>{busy ? "Uploading…" : "Upload"}</button>
      </form>
      <SectionError message={err} />

      {lead.documents.length > 0 && (
        <ul className="mt-4 divide-y divide-rule rounded-lg border border-rule bg-white">
          {lead.documents.map((d) => (
            <li key={d.id} className="flex flex-wrap items-center justify-between gap-3 p-4">
              <div className="min-w-0">
                <div className="truncate text-navy-deep">{d.original_name || d.doc_type_display}</div>
                <div className="text-sm text-navy-soft">
                  {d.doc_type_display} · {fileSize(d.size)} · {d.uploaded_by_name}, {shortDate(d.uploaded_at)}
                  {d.is_verified && <span className="font-medium text-grass"> · Verified</span>}
                </div>
              </div>
              <div className="flex flex-wrap gap-2 text-sm">
                <button className="btn-quiet px-3 py-1.5 text-sm"
                        onClick={() => act(() => staffApi.downloadDocument(d))}>Download</button>
                <button className="btn-quiet px-3 py-1.5 text-sm"
                        onClick={() => act(() => staffApi.updateDocument(d.id, { is_verified: !d.is_verified }))}>
                  {d.is_verified ? "Unverify" : "Mark verified"}
                </button>
                {(!d.is_verified || me?.is_admin) && (
                  <button className="px-3 py-1.5 text-sm text-urgent hover:underline"
                          onClick={() => window.confirm(`Delete ${d.original_name}? This can't be undone.`)
                            && act(() => staffApi.deleteDocument(d.id))}>
                    Delete
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default function LeadDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [lead, setLead] = useState(null);
  const [me, setMe] = useState(null);
  const [staff, setStaff] = useState([]);
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const bail = (err) => {
    if (err.message === "SESSION_EXPIRED") navigate("/staff/login");
    else if (err.message === "PASSWORD_CHANGE_REQUIRED") navigate("/staff/password");
    else setError(err.message);
  };
  // Problems with one action shouldn't blank the whole page.
  const warn = (err) => {
    if (err.message === "SESSION_EXPIRED") navigate("/staff/login");
    else setNotice(err.message);
  };
  const reload = () => staffApi.lead(id).then(setLead).catch(bail);

  useEffect(() => {
    Promise.all([staffApi.lead(id), staffApi.me()])
      .then(([l, u]) => {
        setLead(l);
        setMe(u);
        // Every active staff member, not only those shown on the public site.
        if (u.is_admin) staffApi.team().then(setStaff).catch(() => {});
      })
      .catch(bail);
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  async function patch(data) {
    setSaving(true);
    setNotice("");
    try {
      setLead(await staffApi.updateLead(id, data));
    } catch (err) {
      warn(err);
    } finally {
      setSaving(false);
    }
  }

  async function logCall(e) {
    e.preventDefault();
    if (!note.trim()) return;
    setSaving(true);
    try {
      // is_call_log stamps last_contacted_at on the server, which is what
      // pulls this student off the "needs a call" list.
      await staffApi.addNote(id, { body: note, is_call_log: true });
      setNote("");
      await reload();
    } catch (err) {
      warn(err);
    } finally {
      setSaving(false);
    }
  }

  if (error) {
    // A counsellor opening someone else's student gets 404 from the server.
    // Say so plainly instead of showing DRF's "No Lead matches the given query."
    const missing = /No Lead matches/.test(error);
    return (
      <div className="wrap max-w-prose py-20">
        <p className="text-urgent">
          {missing ? "This student isn't on your list, or the link is wrong." : error}
        </p>
        <Link to="/staff" className="btn-quiet mt-6">Back to your students</Link>
      </div>
    );
  }
  if (!lead) return <p className="wrap py-20 text-navy-soft">Loading…</p>;

  return (
    <div className="wrap max-w-3xl py-8">
      <Link to="/staff" className="text-sm text-navy-soft hover:text-grass">
        Back to the list
      </Link>

      <div className="mt-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl">{lead.full_name}</h1>
          <p className="mt-1 text-navy-soft">
            {lead.created_by_name
              ? `Added by ${lead.created_by_name} (${lead.source || "unknown"})`
              : `Came in via ${lead.source || "unknown"}`}{" "}
            on {shortDate(lead.created_at)}
            {lead.source_detail && ` · ${lead.source_detail}`}
          </p>
        </div>
        <StatusChip status={lead.status} label={lead.status_display} />
      </div>

      {notice && (
        <p className="mt-4 rounded-md border border-urgent/30 bg-urgent/5 px-4 py-3 text-sm text-urgent">
          {notice}
        </p>
      )}

      {/* Everything else on this page is secondary to making the call. */}
      <div className="mt-6 flex flex-wrap gap-3">
        <a href={`tel:${lead.phone.replace(/\s/g, "")}`} className="btn-go">
          Call {lead.phone}
        </a>
        <a href={whatsappLink(lead.phone)} target="_blank" rel="noopener noreferrer" className="btn-quiet">
          WhatsApp
        </a>
      </div>

      {lead.visa_history === "refused" && (
        <div className="mt-6 rounded-lg border border-urgent/30 bg-urgent/5 p-4">
          <h2 className="text-base text-urgent">Previously refused a visa</h2>
          <p className="mt-1 text-sm leading-relaxed text-navy">
            {lead.visa_history_country || "Country not given"}
            {lead.visa_history_date &&
              ` · ${new Date(lead.visa_history_date).toLocaleDateString("en-GB", {
                month: "long", year: "numeric",
              })}`}
            . The next application has to address the refusal directly, so read the
            original decision letter before advising anything.
          </p>
        </div>
      )}

      <dl className="mt-8 grid gap-5 rounded-lg border border-rule bg-white p-5 sm:grid-cols-2">
        <Fact label="Wants to study in" value={lead.countries.join(", ")} />
        <Fact label="Target intake" value={lead.target_intake} />
        <Fact label="Highest qualification" value={lead.highest_qualification} />
        <Fact label="Completed" value={lead.completion_year} />
        <Fact label="Study gap" value={lead.study_gap_years != null && `${lead.study_gap_years} years`} />
        <Fact
          label="Test"
          value={lead.test_type !== "none" && `${lead.test_type.toUpperCase()} ${lead.test_score ?? "—"}`}
        />
        <Fact label="Budget" value={lead.budget_note} />
        <Fact label="Email" value={lead.email} />
        <Fact label="Visa history" value={lead.visa_history_display} />
        <Fact label="Consent"
              value={lead.consent_given && `${lead.consent_method_display}${lead.consent_at ? `, ${shortDate(lead.consent_at)}` : ""}`} />
      </dl>

      {lead.message && (
        <div className="mt-5 rounded-lg border border-rule bg-white p-5">
          <h2 className="text-base">What they told us</h2>
          <p className="mt-2 whitespace-pre-line leading-relaxed text-navy">{lead.message}</p>
        </div>
      )}

      <div className="mt-8 grid gap-4 sm:grid-cols-3">
        <div>
          <label className="label" htmlFor="status">Stage</label>
          <select
            id="status" className="field" value={lead.status} disabled={saving}
            onChange={(e) => patch({ status: e.target.value })}
          >
            {STATUSES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </div>

        <div>
          <label className="label" htmlFor="follow">Next follow-up</label>
          <input
            id="follow" type="date" className="field" disabled={saving}
            value={lead.next_follow_up || ""}
            onChange={(e) => patch({ next_follow_up: e.target.value || null })}
          />
        </div>

        {/* Reassignment is an owner decision. The server strips this field
            from a counsellor's request even if the control were shown. */}
        {me?.is_admin && (
          <div>
            <label className="label" htmlFor="assign">Assigned to</label>
            <select
              id="assign" className="field" value={lead.assigned_to || ""} disabled={saving}
              onChange={(e) => patch({ assigned_to: e.target.value ? Number(e.target.value) : null })}
            >
              <option value="">Nobody yet</option>
              {staff.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </div>
        )}
      </div>

      {lead.status === "lost" && (
        <div className="mt-4">
          <label className="label" htmlFor="lost">Why we lost them</label>
          <input
            id="lost" className="field" defaultValue={lead.lost_reason}
            placeholder="e.g. chose another consultancy, family decided against it"
            onBlur={(e) => e.target.value !== lead.lost_reason && patch({ lost_reason: e.target.value })}
          />
        </div>
      )}

      <section className="mt-8">
        <h2 className="text-xl">Call log</h2>
        <form onSubmit={logCall} className="mt-3">
          <textarea
            className="field" rows={3} value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="What was said, and what happens next…"
          />
          <button className="btn-go mt-3" disabled={saving || !note.trim()}>
            {saving ? "Saving…" : "Log this call"}
          </button>
        </form>

        <div className="mt-6 space-y-4">
          {lead.notes.length === 0 && (
            <p className="text-navy-soft">Nobody has spoken to this student yet.</p>
          )}
          {lead.notes.map((n) => (
            <div key={n.id} className="border-l-2 border-rule pl-4">
              <div className="text-sm text-navy-soft">
                {n.author_name} · {dateTime(n.created_at)}
              </div>
              <p className="mt-1 whitespace-pre-line leading-relaxed text-navy">{n.body}</p>
            </div>
          ))}
        </div>
      </section>

      <Applications lead={lead} me={me} onChange={reload} onError={warn} />
      <Documents lead={lead} me={me} onChange={reload} onError={warn} />

      {lead.history?.length > 0 && (
        <section className="mt-10">
          <h2 className="text-xl">Stage history</h2>
          <ol className="mt-3 space-y-1.5 text-sm text-navy">
            {lead.history.map((h) => (
              <li key={h.id}>
                <span className="text-navy-soft">{dateTime(h.created_at)}</span>
                {" · "}
                {h.from_display ? `${h.from_display} → ${h.to_display}` : `Started as ${h.to_display}`}
                <span className="text-navy-soft"> · {h.changed_by_name}</span>
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}
