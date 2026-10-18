import { Badge, fmt } from "./ui";

export default function Queue({ docs, onOpen }) {
  if (!docs.length)
    return <p className="rounded-xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">No documents here yet.</p>;
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
          <tr>
            {["File", "Type", "PO", "Status", "Issues", "Extractor", "Uploaded"].map((h) => (
              <th key={h} className="px-4 py-3 font-medium">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {docs.map((d) => {
            const issues = (d.discrepancies?.length || 0) + (d.validation_errors?.length || 0);
            return (
              <tr key={d.id} onClick={() => onOpen(d.id)} className="cursor-pointer hover:bg-indigo-50/50">
                <td className="max-w-[260px] truncate px-4 py-3 font-medium text-slate-800">{d.filename}</td>
                <td className="px-4 py-3">{fmt(d.doc_type)}</td>
                <td className="px-4 py-3 font-mono text-xs">{fmt(d.po_number)}</td>
                <td className="px-4 py-3"><Badge status={d.status} /></td>
                <td className="px-4 py-3">{issues || "—"}</td>
                <td className="px-4 py-3 text-xs text-slate-500">{fmt(d.extraction_method)}</td>
                <td className="px-4 py-3 text-xs text-slate-500">{d.created_at ? new Date(d.created_at + "Z").toLocaleString() : "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
