import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import Upload from "./components/Upload";
import Queue from "./components/Queue";
import ReviewPanel from "./components/ReviewPanel";
import { NEEDS_REVIEW, STATUS } from "./components/ui";

const TABS = [
  { key: "REVIEW", label: "Needs review" },
  { key: "ALL", label: "All" },
  { key: "AUTO_APPROVED", label: "Auto-approved" },
  { key: "APPROVED", label: "Approved" },
  { key: "REJECTED", label: "Rejected" },
];

export default function App() {
  const [docs, setDocs] = useState([]);
  const [stats, setStats] = useState({});
  const [tab, setTab] = useState("REVIEW");
  const [open, setOpen] = useState(null);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const [d, s] = await Promise.all([api.list(), api.stats()]);
      setDocs(d); setStats(s); setError(null);
    } catch (e) { setError(e.message); }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const shown = docs.filter((d) =>
    tab === "ALL" ? true : tab === "REVIEW" ? NEEDS_REVIEW.includes(d.status) : d.status === tab);
  const reviewCount = NEEDS_REVIEW.reduce((n, k) => n + (stats[k] || 0), 0);

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Document Agent</h1>
          <p className="text-sm text-slate-500">Autonomous extraction · PO reconciliation · human review</p>
        </div>
        {reviewCount > 0 && (
          <span className="rounded-full bg-amber-100 px-3 py-1 text-sm font-medium text-amber-800">{reviewCount} awaiting review</span>
        )}
      </header>

      {error && <div className="mb-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error}</div>}

      {open ? (
        <ReviewPanel id={open} onBack={() => { setOpen(null); refresh(); }} onChanged={refresh} />
      ) : (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
            {["AUTO_APPROVED", "FLAGGED", "SCHEMA_FAILED", "APPROVED", "REJECTED"].map((k) => (
              <button key={k} onClick={() => setTab(k === "FLAGGED" || k === "SCHEMA_FAILED" ? "REVIEW" : k)}
                className="rounded-xl border border-slate-200 bg-white p-4 text-left shadow-sm hover:border-indigo-300">
                <div className="text-2xl font-bold">{stats[k] || 0}</div>
                <div className="text-xs text-slate-500">{STATUS[k].label}</div>
              </button>
            ))}
          </div>

          <Upload onDone={refresh} />

          <div>
            <div className="mb-3 flex gap-1 border-b border-slate-200">
              {TABS.map((t) => (
                <button key={t.key} onClick={() => setTab(t.key)}
                  className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium ${
                    tab === t.key ? "border-indigo-600 text-indigo-700" : "border-transparent text-slate-500 hover:text-slate-800"}`}>
                  {t.label}
                </button>
              ))}
            </div>
            <Queue docs={shown} onOpen={setOpen} />
          </div>
        </div>
      )}
    </div>
  );
}
