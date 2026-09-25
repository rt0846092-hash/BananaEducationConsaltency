import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { content, staffApi } from "../auth";

/**
 * Owner only: everything students see on the public website — destinations,
 * universities and their courses and fees, scholarships and language classes.
 * Changes appear on the site as soon as they're saved.
 */

const LEVELS = [["foundation", "Foundation"], ["diploma", "Diploma"], ["bachelor", "Bachelor"],
                ["master", "Master"], ["phd", "PhD"]];
const TESTS = [["ielts", "IELTS"], ["pte", "PTE"], ["toefl", "TOEFL"], ["topik", "TOPIK"], ["other", "Other"]];
const today = () => new Date().toISOString().slice(0, 10);
const fmtDate = (d) => d ? new Date(d).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }) : "";

/** A small form built from a list of field descriptions. */
function ItemForm({ fields, initial, onSave, onCancel, onDelete, saveLabel = "Save" }) {
  const [values, setValues] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const data = { ...values };
    // Empty optional numbers and dates are "not set", not zero or an invalid date.
    fields.forEach((f) => {
      if (["number", "date", "select"].includes(f.type) && data[f.key] === "") data[f.key] = null;
    });
    try {
      await onSave(data);
    } catch (err) {
      const b = err.body || {};
      const first = Object.entries(b)[0];
      setError(first && first[0] !== "detail"
        ? `${fields.find((f) => f.key === first[0])?.label || first[0]}: ${[].concat(first[1])[0]}`
        : err.message);
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="grid gap-4 rounded-lg border border-grass/40 bg-white p-5 sm:grid-cols-2">
      {fields.map((f) => {
        const id = `f-${f.key}`;
        const common = {
          id, value: values[f.key] ?? "", required: f.required,
          onChange: (e) => setValues({ ...values, [f.key]: e.target.value }),
        };
        if (f.type === "checkbox") {
          return (
            <label key={f.key} className="flex items-center gap-3 text-sm text-navy sm:col-span-2">
              <input type="checkbox" className="h-4 w-4 accent-grass" checked={!!values[f.key]}
                     onChange={(e) => setValues({ ...values, [f.key]: e.target.checked })} />
              {f.label}
            </label>
          );
        }
        return (
          <div key={f.key} className={f.wide ? "sm:col-span-2" : ""}>
            <label className="label" htmlFor={id}>{f.label}</label>
            {f.type === "textarea" ? (
              <textarea className="field" rows={3} {...common} />
            ) : f.type === "select" ? (
              <select className="field" {...common}>
                {!f.required && <option value="">—</option>}
                {f.options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            ) : (
              <input className="field" type={f.type || "text"} min={f.type === "number" ? 0 : undefined}
                     step={f.step} placeholder={f.placeholder} {...common} />
            )}
            {f.help && <p className="mt-1 text-sm text-navy-soft">{f.help}</p>}
          </div>
        );
      })}
      {error && <p className="rounded-md border border-urgent/30 bg-urgent/5 px-4 py-3 text-sm text-urgent sm:col-span-2">{error}</p>}
      <div className="flex flex-wrap gap-3 sm:col-span-2">
        <button className="btn-go" disabled={busy}>{busy ? "Saving…" : saveLabel}</button>
        <button type="button" className="btn-quiet" onClick={onCancel}>Cancel</button>
        {onDelete && (
          <button type="button" className="ml-auto text-sm text-urgent hover:underline"
                  onClick={async () => {
                    if (!window.confirm("Delete this? It can't be undone.")) return;
                    try { await onDelete(); } catch (err) { setError(err.message); }
                  }}>
            Delete
          </button>
        )}
      </div>
    </form>
  );
}

/** A list where each row opens into an edit form, with "+ Add" on top. */
function EditableList({ title, items, fields, blank, summary, api, reload, addLabel, extra }) {
  const [editing, setEditing] = useState(null); // item id, or "new"
  const [notice, setNotice] = useState("");

  const done = async (msg) => {
    setEditing(null);
    setNotice(msg);
    await reload();
  };

  return (
    <section className="mt-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        {title && <h2 className="text-xl">{title}</h2>}
        {editing !== "new" && (
          <button className="btn-quiet px-4 py-2 text-sm" onClick={() => { setNotice(""); setEditing("new"); }}>
            + {addLabel}
          </button>
        )}
      </div>
      {notice && <p className="mt-3 text-sm text-grass-dark">{notice}</p>}
      {editing === "new" && (
        <div className="mt-3">
          <ItemForm fields={fields} initial={blank} saveLabel={addLabel}
                    onSave={async (d) => { await api.add(d); await done("Added."); }}
                    onCancel={() => setEditing(null)} />
        </div>
      )}
      <ul className="mt-3 space-y-2">
        {items.map((item) => (
          <li key={item.id}>
            {editing === item.id ? (
              <ItemForm fields={fields} initial={item}
                        onSave={async (d) => { await api.update(item.id, d); await done("Saved."); }}
                        onDelete={async () => { await api.remove(item.id); await done("Deleted."); }}
                        onCancel={() => setEditing(null)} />
            ) : (
              <div className={`flex flex-wrap items-start justify-between gap-3 rounded-lg border border-rule bg-white p-4 ${
                item.is_active === false ? "opacity-60" : ""}`}>
                <div className="min-w-0 flex-1">{summary(item)}</div>
                <div className="flex flex-wrap items-center gap-3">
                  {extra && extra(item)}
                  <button className="text-sm font-medium text-navy hover:underline"
                          aria-label={`Edit ${item.name || item.title || item.test_type}`}
                          onClick={() => { setNotice(""); setEditing(item.id); }}>Edit</button>
                </div>
              </div>
            )}
          </li>
        ))}
        {items.length === 0 && editing !== "new" && <li className="text-navy-soft">Nothing here yet.</li>}
      </ul>
    </section>
  );
}

function Hidden({ item }) {
  return item.is_active === false
    ? <span className="ml-2 rounded bg-paper px-2 py-0.5 text-xs text-navy-soft">Hidden</span>
    : null;
}

// ---------------------------------------------------------------------------

function Destinations({ countries, reload }) {
  return (
    <EditableList
      items={countries} api={content("countries")} reload={reload} addLabel="Add destination"
      blank={{ name: "", summary: "", visa_notes: "", sort_order: countries.length, is_active: true }}
      fields={[
        { key: "name", label: "Country or region", required: true },
        { key: "sort_order", label: "Position on the home page", type: "number", help: "Smaller numbers come first." },
        { key: "summary", label: "Short description (on the home page card)", type: "textarea", wide: true },
        { key: "visa_notes", label: "What the visa asks for", type: "textarea", wide: true },
        { key: "is_active", label: "Show on the website", type: "checkbox" },
      ]}
      summary={(c) => (
        <>
          <span className="font-medium text-navy-deep">{c.name}</span><Hidden item={c} />
          <div className="text-sm text-navy-soft">{c.university_count} universities · /study/{c.slug}</div>
        </>
      )}
    />
  );
}

function Courses({ uni, reload }) {
  return (
    <div className="mt-2 border-l-2 border-rule pl-4">
      <EditableList
        items={uni.courses} api={content("courses")} reload={reload} addLabel="Add course"
        blank={{ university: uni.id, name: "", level: "master", duration_months: "", tuition_fee: "",
                 currency: "USD", intake_months: "", is_active: true }}
        fields={[
          { key: "name", label: "Course name", required: true, wide: true },
          { key: "level", label: "Level", type: "select", options: LEVELS, required: true },
          { key: "duration_months", label: "Length (months)", type: "number" },
          { key: "tuition_fee", label: "Total tuition fee", type: "number", step: "0.01" },
          { key: "currency", label: "Currency", placeholder: "USD, AUD, GBP…" },
          { key: "intake_months", label: "Intakes", placeholder: "Feb, Jul", wide: true },
          { key: "is_active", label: "Show on the website", type: "checkbox" },
        ]}
        summary={(c) => (
          <>
            <span className="text-navy">{c.name}</span><Hidden item={c} />
            <div className="text-sm text-navy-soft">
              {[c.duration_months && `${c.duration_months} months`,
                c.tuition_fee && `${c.currency} ${Number(c.tuition_fee).toLocaleString()}`,
                c.intake_months].filter(Boolean).join(" · ")}
            </div>
          </>
        )}
      />
    </div>
  );
}

function Universities({ countries }) {
  const [country, setCountry] = useState(countries[0]?.id || "");
  const [unis, setUnis] = useState([]);
  const [open, setOpen] = useState(null);
  const api = content("universities");
  const reload = () => (country ? api.list(`?country=${country}`).then(setUnis) : Promise.resolve());

  useEffect(() => { reload(); }, [country]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <>
      <div className="mt-6 max-w-xs">
        <label className="label" htmlFor="uni-country">Destination</label>
        <select id="uni-country" className="field" value={country} onChange={(e) => setCountry(e.target.value)}>
          {countries.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
      </div>
      <EditableList
        items={unis} api={api} reload={reload} addLabel="Add university"
        blank={{ country: Number(country), name: "", city: "", website: "", description: "",
                 is_partner: true, is_active: true, last_verified_on: today() }}
        fields={[
          { key: "name", label: "University", required: true },
          { key: "city", label: "City" },
          { key: "website", label: "Website", type: "url", placeholder: "https://…", wide: true },
          { key: "description", label: "Description", type: "textarea", wide: true },
          { key: "last_verified_on", label: "Fees last checked", type: "date",
            help: "Shown to students. Update it whenever you confirm the fees." },
          { key: "country", label: "Destination", type: "select", required: true,
            options: countries.map((c) => [c.id, c.name]) },
          { key: "is_partner", label: "Partner (we earn commission here)", type: "checkbox" },
          { key: "is_active", label: "Show on the website", type: "checkbox" },
        ]}
        summary={(u) => (
          <>
            <span className="font-medium text-navy-deep">{u.name}</span><Hidden item={u} />
            <div className="text-sm text-navy-soft">
              {[u.city, `${u.courses.length} ${u.courses.length === 1 ? "course" : "courses"}`,
                u.last_verified_on ? `fees checked ${fmtDate(u.last_verified_on)}` : "fees never checked"]
                .filter(Boolean).join(" · ")}
            </div>
            {open === u.id && <Courses uni={u} reload={reload} />}
          </>
        )}
        extra={(u) => (
          <>
            <button className="text-sm text-navy hover:underline"
                    onClick={() => setOpen(open === u.id ? null : u.id)}>
              {open === u.id ? "Hide courses" : "Courses & fees"}
            </button>
            <button className="text-sm text-grass hover:underline" title="Sets 'fees last checked' to today"
                    onClick={async () => { await api.action(u.id, "mark-checked"); reload(); }}>
              Fees checked today
            </button>
          </>
        )}
      />
    </>
  );
}

function Scholarships({ countries }) {
  const [items, setItems] = useState([]);
  const api = content("scholarships");
  const reload = () => api.list().then(setItems);
  useEffect(() => { reload(); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const name = (id) => countries.find((c) => c.id === id)?.name || "";

  return (
    <EditableList
      items={items} api={api} reload={reload} addLabel="Add scholarship"
      blank={{ country: countries[0]?.id, name: "", amount_note: "", eligibility: "", deadline: "",
               link: "", is_active: true }}
      fields={[
        { key: "name", label: "Scholarship", required: true, wide: true },
        { key: "country", label: "Destination", type: "select", required: true,
          options: countries.map((c) => [c.id, c.name]) },
        { key: "amount_note", label: "Worth", placeholder: "Up to 50% of tuition" },
        { key: "deadline", label: "Deadline", type: "date" },
        { key: "link", label: "Official page", type: "url", placeholder: "https://…" },
        { key: "eligibility", label: "Who can get it", type: "textarea", wide: true },
        { key: "is_active", label: "Show on the website", type: "checkbox" },
      ]}
      summary={(s) => (
        <>
          <span className="font-medium text-navy-deep">{s.name}</span><Hidden item={s} />
          <div className="text-sm text-navy-soft">
            {[name(s.country), s.amount_note, s.deadline && `closes ${fmtDate(s.deadline)}`].filter(Boolean).join(" · ")}
          </div>
        </>
      )}
    />
  );
}

function Classes({ staff }) {
  const [items, setItems] = useState([]);
  const api = content("batches");
  const reload = () => api.list().then(setItems);
  useEffect(() => { reload(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <>
      <p className="mt-6 max-w-prose text-sm text-navy-soft">
        Classes appear on the home page from today until their start date — the next six are shown.
      </p>
      <EditableList
        items={items} api={api} reload={reload} addLabel="Add class"
        blank={{ test_type: "ielts", title: "", start_date: today(), schedule_note: "",
                 duration_weeks: 6, fee: "", total_seats: 20, seats_taken: 0, instructor: "", is_active: true }}
        fields={[
          { key: "test_type", label: "Test", type: "select", options: TESTS, required: true },
          { key: "start_date", label: "Starts", type: "date", required: true },
          { key: "schedule_note", label: "When", placeholder: "Sun–Thu, 7–9 am" },
          { key: "duration_weeks", label: "Length (weeks)", type: "number" },
          { key: "fee", label: "Fee (NPR)", type: "number" },
          { key: "instructor", label: "Teacher", type: "select", options: staff.map((p) => [p.id, p.name]) },
          { key: "total_seats", label: "Seats", type: "number" },
          { key: "seats_taken", label: "Seats already taken", type: "number",
            help: "Update as students join. The site shows how many are left." },
          { key: "is_active", label: "Show on the website", type: "checkbox" },
        ]}
        summary={(b) => (
          <>
            <span className="font-medium text-navy-deep">{b.test_type.toUpperCase()} · starts {fmtDate(b.start_date)}</span>
            <Hidden item={b} />
            <div className="text-sm text-navy-soft">
              {[b.schedule_note, `${b.seats_left} of ${b.total_seats} seats left`,
                new Date(b.start_date) < new Date(today()) && "already started"].filter(Boolean).join(" · ")}
            </div>
          </>
        )}
      />
    </>
  );
}

const TABS = [["destinations", "Destinations"], ["universities", "Universities & fees"],
              ["scholarships", "Scholarships"], ["classes", "Language classes"]];

export default function Content() {
  const navigate = useNavigate();
  const [tab, setTab] = useState("destinations");
  const [countries, setCountries] = useState(null);
  const [staff, setStaff] = useState([]);
  const [error, setError] = useState("");
  const reloadCountries = () => content("countries").list().then(setCountries);

  useEffect(() => {
    Promise.all([reloadCountries(), staffApi.team().then(setStaff)]).catch((err) => {
      if (err.message === "SESSION_EXPIRED") navigate("/staff/login");
      else setError(err.message);
    });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (error) {
    return (
      <div className="wrap py-20">
        <p className="text-urgent">{error}</p>
        <p className="mt-2 text-navy-soft">This page is for the office owner.</p>
      </div>
    );
  }
  if (!countries) return <p className="wrap py-20 text-navy-soft">Loading…</p>;

  return (
    <div className="wrap max-w-4xl py-8">
      <h1 className="text-2xl sm:text-3xl">Website</h1>
      <p className="mt-1.5 max-w-prose text-navy-soft">
        What students see on the public site. Changes appear as soon as you save.
        Untick "Show on the website" to hide something without losing it.
      </p>
      <div className="mt-6 flex flex-wrap gap-1.5" role="tablist">
        {TABS.map(([key, label]) => (
          <button key={key} role="tab" aria-selected={tab === key} onClick={() => setTab(key)}
                  className={`rounded-full px-4 py-2 text-sm ${
                    tab === key ? "bg-navy-deep text-white" : "border border-rule bg-white text-navy hover:border-navy-soft"}`}>
            {label}
          </button>
        ))}
      </div>
      {tab === "destinations" && <Destinations countries={countries} reload={reloadCountries} />}
      {tab === "universities" && <Universities countries={countries} />}
      {tab === "scholarships" && <Scholarships countries={countries} />}
      {tab === "classes" && <Classes staff={staff} />}
    </div>
  );
}
