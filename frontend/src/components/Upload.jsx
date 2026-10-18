import { useRef, useState } from "react";
import { api } from "../api";

export default function Upload({ onDone }) {
  const [drag, setDrag] = useState(false);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  const input = useRef();

  async function handle(files) {
    const list = [...files].filter((f) => f.name.toLowerCase().endsWith(".pdf"));
    if (!list.length) return setMsg({ err: true, text: "Please choose PDF files." });
    setBusy(true);
    setMsg(null);
    let last;
    try {
      for (const f of list) last = await api.upload(f);
      setMsg({ text: `Processed ${list.length} file(s). Last result: ${last.status.replace("_", " ")}` });
      onDone(last);
    } catch (e) {
      setMsg({ err: true, text: e.message });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => { e.preventDefault(); setDrag(false); handle(e.dataTransfer.files); }}
      onClick={() => !busy && input.current.click()}
      className={`cursor-pointer rounded-xl border-2 border-dashed px-6 py-8 text-center transition ${
        drag ? "border-indigo-500 bg-indigo-50" : "border-slate-300 bg-white hover:border-indigo-400"
      }`}
    >
      <input ref={input} type="file" accept="application/pdf" multiple hidden onChange={(e) => handle(e.target.files)} />
      <p className="text-sm font-medium text-slate-700">
        {busy ? "Extracting and reconciling…" : "Drag & drop invoices or bills of lading here, or click to browse"}
      </p>
      <p className="mt-1 text-xs text-slate-500">PDF only · extraction + PO reconciliation run automatically</p>
      {msg && <p className={`mt-3 text-sm ${msg.err ? "text-rose-600" : "text-emerald-700"}`}>{msg.text}</p>}
    </div>
  );
}
