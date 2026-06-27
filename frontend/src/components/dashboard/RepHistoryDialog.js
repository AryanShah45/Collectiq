import { useQuery } from "@tanstack/react-query";
import { getRepHistory } from "@/lib/api";
import { formatINR } from "@/lib/calc";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { X, Loader2, TrendingUp } from "lucide-react";

function fmtAxis(n) {
  if (Math.abs(n) >= 1e7) return `${(n / 1e7).toFixed(1)}Cr`;
  if (Math.abs(n) >= 1e5) return `${(n / 1e5).toFixed(1)}L`;
  return `${n}`;
}

export default function RepHistoryDialog({ name, onClose }) {
  const { data, isLoading } = useQuery({
    queryKey: ["rep-history", name],
    queryFn: () => getRepHistory(name),
    enabled: !!name,
  });
  const points = (data?.points || []).map((p) => ({ ...p, label: p.week_label || p.meeting_date }));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={onClose} data-testid="rep-history-dialog">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between p-5 border-b border-border sticky top-0 bg-white">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            <h3 className="text-lg font-medium">{name} — history</h3>
          </div>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground" data-testid="close-rep-history"><X className="h-5 w-5" /></button>
        </div>

        <div className="p-5">
          {isLoading ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground py-12 justify-center"><Loader2 className="h-4 w-4 animate-spin" /> Loading history…</div>
          ) : points.length === 0 ? (
            <p className="text-sm text-muted-foreground py-12 text-center">No history yet — this rep appears in only one or no weeks.</p>
          ) : (
            <>
              <div className="text-[11px] uppercase tracking-wider text-muted-foreground mb-2">Outstanding vs Collected</div>
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={points} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
                    <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                    <YAxis tickFormatter={fmtAxis} tick={{ fontSize: 11 }} />
                    <Tooltip formatter={(v) => formatINR(v)} />
                    <Legend />
                    <Line type="monotone" dataKey="outstanding" name="Outstanding" stroke="#000000" strokeWidth={2} dot={{ r: 3 }} />
                    <Line type="monotone" dataKey="collected" name="Collected" stroke="#16A34A" strokeWidth={2} dot={{ r: 3 }} />
                    <Line type="monotone" dataKey="d90" name="90-day" stroke="#DC2626" strokeWidth={2} dot={{ r: 3 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              <div className="mt-5 overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-[10px] uppercase tracking-wider text-muted-foreground border-b border-border">
                      <th className="text-left py-2 px-2">Week</th>
                      <th className="text-right py-2 px-2">Outstanding</th>
                      <th className="text-right py-2 px-2">90-day</th>
                      <th className="text-right py-2 px-2">Collected</th>
                      <th className="text-right py-2 px-2">Coll %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {points.map((p, i) => (
                      <tr key={i} className="border-b border-border/50">
                        <td className="py-2 px-2">{p.meeting_date}</td>
                        <td className="py-2 px-2 text-right font-mono">{formatINR(p.outstanding)}</td>
                        <td className="py-2 px-2 text-right font-mono text-[#DC2626]">{formatINR(p.d90)}</td>
                        <td className="py-2 px-2 text-right font-mono text-[#16A34A]">{formatINR(p.collected)}</td>
                        <td className="py-2 px-2 text-right font-mono">{p.coll_pct.toFixed(1)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
