export const STATUS = {
  AUTO_APPROVED: { label: "Auto-approved", cls: "bg-emerald-100 text-emerald-800 ring-emerald-200" },
  FLAGGED: { label: "Flagged", cls: "bg-amber-100 text-amber-800 ring-amber-200" },
  SCHEMA_FAILED: { label: "Schema failed", cls: "bg-rose-100 text-rose-800 ring-rose-200" },
  APPROVED: { label: "Approved", cls: "bg-sky-100 text-sky-800 ring-sky-200" },
  REJECTED: { label: "Rejected", cls: "bg-slate-200 text-slate-700 ring-slate-300" },
  PENDING: { label: "Pending", cls: "bg-slate-100 text-slate-600 ring-slate-200" },
};

export const NEEDS_REVIEW = ["FLAGGED", "SCHEMA_FAILED"];

export function Badge({ status }) {
  const s = STATUS[status] || STATUS.PENDING;
  return <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${s.cls}`}>{s.label}</span>;
}

export function fmt(v, field = "") {
  if (v === null || v === undefined || v === "") return "—";
  if (typeof v === "number") {
    const money = /cost|amount|price|subtotal|tax/.test(field);
    return money ? v.toLocaleString(undefined, { style: "currency", currency: "USD" }) : v.toLocaleString();
  }
  return String(v);
}

export function Card({ title, children, className = "" }) {
  return (
    <section className={`rounded-xl border border-slate-200 bg-white shadow-sm ${className}`}>
      {title && <h3 className="border-b border-slate-100 px-4 py-3 text-sm font-semibold text-slate-700">{title}</h3>}
      <div className="p-4">{children}</div>
    </section>
  );
}
