import { Fragment } from "react";
import { Card } from "@/components/ui/card";
import { bucketCell, formatINR, BUCKETS } from "@/lib/calc";

function Money({ v, className = "" }) {
  return <span className={`font-mono tabular-nums text-xs ${className}`}>{formatINR(v)}</span>;
}

export default function CollectionTable({ meeting }) {
  const reps = meeting?.reps || [];
  const buckets = BUCKETS; // d90,d60,d30,othera

  const totals = {};
  buckets.forEach((b) => (totals[b.key] = { mbs: 0, mcorp: 0, total: 0 }));
  let tOutMbs = 0, tOutMcorp = 0, tOut = 0, tColl = 0;

  const rows = reps.map((r) => {
    const cells = {};
    let oMbs = 0, oMcorp = 0;
    buckets.forEach((b) => {
      const c = bucketCell(r, b.key);
      cells[b.key] = c;
      totals[b.key].mbs += c.mbs; totals[b.key].mcorp += c.mcorp; totals[b.key].total += c.total;
      oMbs += c.mbs; oMcorp += c.mcorp;
    });
    const out = oMbs + oMcorp;
    const coll = r.weekly_collection || 0;
    tOutMbs += oMbs; tOutMcorp += oMcorp; tOut += out; tColl += coll;
    return { name: r.name, cells, oMbs, oMcorp, out, coll, pct: out ? (coll / out) * 100 : 0 };
  });

  return (
    <Card className="shadow-none overflow-hidden" data-testid="collection-table">
      <div className="p-6 pb-3">
        <h3 className="text-base font-medium">Collection Outstanding — Company-wise Dues</h3>
        <p className="text-xs text-muted-foreground mt-1">
          Each aging bucket shown for MBS, MCORP and Total. New Target = total outstanding (90+60+30+Other).
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-right">
          <thead>
            <tr className="border-y border-border bg-secondary/60">
              <th rowSpan={2} className="sticky left-0 bg-secondary/60 text-left px-4 py-2 text-[11px] uppercase tracking-wider text-muted-foreground">Rep</th>
              {buckets.map((b) => (
                <th key={b.key} colSpan={3} className="px-3 py-1.5 text-center text-[11px] uppercase tracking-wider border-l border-border">
                  <span className="inline-flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-sm" style={{ background: b.color }} />{b.label}
                  </span>
                </th>
              ))}
              <th colSpan={3} className="px-3 py-1.5 text-center text-[11px] uppercase tracking-wider border-l border-border bg-black text-white">Total Outstanding</th>
              <th rowSpan={2} className="px-3 py-2 text-[11px] uppercase tracking-wider border-l border-border">Collected</th>
              <th rowSpan={2} className="px-3 py-2 text-[11px] uppercase tracking-wider">Coll %</th>
            </tr>
            <tr className="border-b border-border bg-secondary/40 text-[10px] uppercase tracking-wider text-muted-foreground">
              {buckets.map((b) => (
                <Fragment key={b.key}>
                  <th className="px-2 py-1 border-l border-border font-medium">MBS</th>
                  <th className="px-2 py-1 font-medium">MCORP</th>
                  <th className="px-2 py-1 font-medium">Total</th>
                </Fragment>
              ))}
              <th className="px-2 py-1 border-l border-border font-medium">MBS</th>
              <th className="px-2 py-1 font-medium">MCORP</th>
              <th className="px-2 py-1 font-medium">Total</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.name} className="border-b border-border hover:bg-secondary/30" data-testid={`collection-row-${r.name}`}>
                <td className="sticky left-0 bg-white text-left px-4 py-2.5 text-sm font-medium whitespace-nowrap">{r.name}</td>
                {buckets.map((b) => (
                  <Fragment key={b.key}>
                    <td className="px-2 py-2.5 border-l border-border/60"><Money v={r.cells[b.key].mbs} className="text-muted-foreground" /></td>
                    <td className="px-2 py-2.5"><Money v={r.cells[b.key].mcorp} className="text-muted-foreground" /></td>
                    <td className="px-2 py-2.5"><Money v={r.cells[b.key].total} className="font-semibold" /></td>
                  </Fragment>
                ))}
                <td className="px-2 py-2.5 border-l border-border bg-secondary/20"><Money v={r.oMbs} /></td>
                <td className="px-2 py-2.5 bg-secondary/20"><Money v={r.oMcorp} /></td>
                <td className="px-2 py-2.5 bg-secondary/20"><Money v={r.out} className="font-semibold" /></td>
                <td className="px-3 py-2.5 border-l border-border"><Money v={r.coll} className="text-[#16A34A]" /></td>
                <td className="px-3 py-2.5">
                  <span className={`font-mono tabular-nums text-xs font-semibold ${r.pct >= 12 ? "text-[#16A34A]" : r.pct >= 6 ? "text-[#F59E0B]" : "text-[#DC2626]"}`}>{r.pct.toFixed(1)}%</span>
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t-2 border-black bg-secondary/60 font-semibold">
              <td className="sticky left-0 bg-secondary/60 text-left px-4 py-2.5 text-xs uppercase tracking-wider">Total</td>
              {buckets.map((b) => (
                <Fragment key={b.key}>
                  <td className="px-2 py-2.5 border-l border-border"><Money v={totals[b.key].mbs} /></td>
                  <td className="px-2 py-2.5"><Money v={totals[b.key].mcorp} /></td>
                  <td className="px-2 py-2.5"><Money v={totals[b.key].total} /></td>
                </Fragment>
              ))}
              <td className="px-2 py-2.5 border-l border-border bg-black text-white"><Money v={tOutMbs} className="!text-white" /></td>
              <td className="px-2 py-2.5 bg-black text-white"><Money v={tOutMcorp} className="!text-white" /></td>
              <td className="px-2 py-2.5 bg-black text-white"><Money v={tOut} className="!text-white" /></td>
              <td className="px-3 py-2.5 border-l border-border"><Money v={tColl} className="text-[#16A34A]" /></td>
              <td className="px-3 py-2.5"><span className="font-mono text-xs">{tOut ? ((tColl / tOut) * 100).toFixed(1) : 0}%</span></td>
            </tr>
          </tfoot>
        </table>
      </div>
    </Card>
  );
}
