import { useEffect, useState } from "react";
import { api } from "../api";
import { Badge, Card, NEEDS_REVIEW, fmt } from "./ui";

const SEV = { high: "text-rose-600", medium: "text-amber-600", low: "text-slate-500" };

export default function ReviewPanel({ id, onBack, onChanged }) {
  const [doc, setDoc] = useState(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  useEffect(() => { api.get(id).then(setDoc).catch((e) => setErr(e.message)); }, [id]);

  async function act(fn) {
    setBusy(true); setErr(null);
    try { const d = await fn(); setDoc(d); onChanged(); } catch (e) { setErr(e.message); } finally { setBusy(false); }
  }

  if (err && !doc) return <p className="text-rose-600">{err}</p>;
  if (!doc) return <p className="text-slate-500">Loading…</p>;

  const ex = doc.extracted_data || {};
  const po = doc.expected_po;
  const bad = new Set((doc.discrepancies || []).map((d) => d.field));
  const reviewable = NEEDS_REVIEW.includes(doc.status);

  const rows = [
    ["po_number", "PO number"], ["carrier_name", "Carrier"], ["total_cost", "Total cost"],
    ["total_weight", "Total weight (kg)"], ["delivery_date", "Delivery date"],
  ].map(([k, label]) => {
    const expKey = { total_cost: "total_amount", carrier_name: "carrier" }[k] || k;
    return { k, label, ex: ex[k], exp: po ? po[expKey] : null };
  });

  return (
    <div>
      <button onClick={onBack} className="mb-4 text-sm font-medium text-indigo-600 hover:underline">← Back to queue</button>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <h2 className="text-xl font-semibold">{doc.filename}</h2>
        <Badge status={doc.status} />
        <span className="text-xs text-slate-500">via {doc.extraction_method}</span>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Original document" className="lg:sticky lg:top-4 lg:self-start">
          <iframe title="pdf" src={api.fileUrl(doc.id)} className="h-[75vh] w-full rounded-md border border-slate-200" />
        </Card>

        <div className="space-y-4">
          {doc.validation_errors?.length > 0 && (
            <Card title="Schema validation failures" className="border-rose-200">
              <ul className="space-y-2 text-sm text-rose-700">
                {doc.validation_errors.map((e, i) => <li key={i} className="rounded bg-rose-50 px-3 py-2 font-mono text-xs">{e}</li>)}
              </ul>
              <p className="mt-3 text-xs text-slate-500">The extraction failed assertion checks, so it was not reconciled automatically.</p>
            </Card>
          )}

          {doc.discrepancies?.length > 0 && (
            <Card title={`Discrepancies (${doc.discrepancies.length})`} className="border-amber-200">
              <ul className="space-y-2 text-sm">
                {doc.discrepancies.map((d, i) => (
                  <li key={i} className="rounded bg-amber-50 px-3 py-2">
                    <span className={`mr-2 text-xs font-semibold uppercase ${SEV[d.severity]}`}>{d.severity}</span>
                    {d.message}
                  </li>
                ))}
              </ul>
            </Card>
          )}

          <Card title="Extracted vs Purchase Order">
            {!po && <p className="mb-3 text-sm text-amber-700">No matching PO found in the database.</p>}
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase text-slate-500">
                <tr><th className="pb-2">Field</th><th className="pb-2">Extracted</th><th className="pb-2">PO record</th></tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {rows.map((r) => (
                  <tr key={r.k} className={bad.has(r.k) ? "bg-rose-50" : ""}>
                    <td className="py-2 pr-2 text-slate-600">{r.label}</td>
                    <td className={`py-2 pr-2 font-medium ${bad.has(r.k) ? "text-rose-700" : ""}`}>{fmt(r.ex, r.k)}</td>
                    <td className="py-2 font-medium">{fmt(r.exp, r.k === "total_cost" ? "total_cost" : r.k)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>

          {(ex.line_items?.length > 0 || po?.line_items?.length > 0) && (
            <Card title="Line items">
              <div className="grid gap-4 md:grid-cols-2">
                {[["Invoice", ex.line_items], ["PO", po?.line_items]].map(([t, items]) => (
                  <div key={t}>
                    <p className="mb-1 text-xs font-semibold uppercase text-slate-500">{t}</p>
                    <table className="w-full text-xs">
                      <tbody className="divide-y divide-slate-100">
                        {(items || []).map((li, i) => (
                          <tr key={i}>
                            <td className="py-1.5 pr-2">{li.description}</td>
                            <td className="py-1.5 pr-2 text-right">{li.quantity} × {fmt(li.unit_price, "price")}</td>
                            <td className="py-1.5 text-right font-medium">{fmt(li.amount, "amount")}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ))}
              </div>
            </Card>
          )}

          <Card title="Decision">
            {reviewable ? (
              <>
                <textarea value={note} onChange={(e) => setNote(e.target.value)} placeholder="Reviewer note (optional)"
                  className="mb-3 w-full rounded-md border border-slate-300 p-2 text-sm focus:border-indigo-500 focus:outline-none" rows={2} />
                <div className="flex flex-wrap gap-2">
                  <button disabled={busy} onClick={() => act(() => api.approve(doc.id, note))}
                    className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50">Approve override</button>
                  <button disabled={busy} onClick={() => act(() => api.reject(doc.id, note))}
                    className="rounded-md bg-rose-600 px-4 py-2 text-sm font-medium text-white hover:bg-rose-700 disabled:opacity-50">Reject</button>
                  <button disabled={busy} onClick={() => act(() => api.reprocess(doc.id))}
                    className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50">Re-run extraction</button>
                </div>
              </>
            ) : (
              <p className="text-sm text-slate-600">
                This document is <strong>{doc.status.replace("_", " ").toLowerCase()}</strong>.
                {doc.reviewer_note && <> Reviewer note: “{doc.reviewer_note}”</>}
              </p>
            )}
            {err && <p className="mt-3 text-sm text-rose-600">{err}</p>}
          </Card>

          <details className="rounded-xl border border-slate-200 bg-white p-4 text-sm shadow-sm">
            <summary className="cursor-pointer font-semibold text-slate-700">Extraction audit trail</summary>
            <ul className="mt-3 space-y-1 text-xs">
              {(doc.extraction_trail || []).map((t, i) => (
                <li key={i} className="rounded bg-slate-50 px-2 py-1.5">
                  <span className={t.ok ? "text-emerald-600" : "text-rose-600"}>{t.ok ? "✓" : "✗"}</span>{" "}
                  <strong>{t.provider}</strong> attempt {t.attempt}
                  {t.errors?.length > 0 && <div className="mt-1 break-words text-slate-500">{t.errors.join("; ").slice(0, 220)}</div>}
                </li>
              ))}
            </ul>
          </details>
        </div>
      </div>
    </div>
  );
}
