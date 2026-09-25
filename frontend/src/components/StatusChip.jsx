/**
 * Colour alone can't carry the meaning — roughly one man in twelve can't
 * reliably separate red from green — so every chip shows its label too.
 */
const TONE = {
  new: "bg-paper text-navy border-rule",
  contacted: "bg-navy-deep/5 text-navy border-navy-soft/30",
  counselling: "bg-navy-deep/5 text-navy border-navy-soft/30",
  docs_pending: "bg-urgent/10 text-urgent border-urgent/25",
  applied: "bg-grass-pale text-grass-dark border-grass/25",
  offer: "bg-grass-pale text-grass-dark border-grass/25",
  visa_filed: "bg-grass-pale text-grass-dark border-grass/25",
  enrolled: "bg-grass text-white border-grass",
  lost: "bg-paper text-navy-soft border-rule line-through",
};

export default function StatusChip({ status, label }) {
  return (
    <span
      className={`shrink-0 rounded-full border px-2.5 py-1 text-xs font-medium ${
        TONE[status] || TONE.new
      }`}
    >
      {label || status}
    </span>
  );
}
