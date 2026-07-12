import { useQuery } from "@tanstack/react-query";
import { getRepHistory } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { formatINR, BUCKETS } from "@/lib/calc";
import { Card } from "@/components/ui/card";
import KpiCard from "@/components/dashboard/KpiCard";
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
} from "recharts";
import { Loader2, Wallet, HandCoins, Gauge, UserRound } from "lucide-react";

const fmtAxis = (n) => Math.round(Number(n) || 0).toLocaleString("en-IN");

export default function MyPerformance() {
  const { user } = useAuth();
  const repName = user?.rep_name || "";
  const { data, isLoading } = useQuery({
    queryKey: ["my-history", repName],
    queryFn: () => getRepHistory(repName),
    enabled: !!repName,
  });

  if (!repName) {
    return (
      <div className="text-center py-32" data-testid="my-page-unlinked">
        <UserRound className="h-10 w-10 mx-auto text-muted-foreground mb-4" />
        <h2 className="text-xl font-medium">Your account isn&apos;t linked to a representative yet</h2>
        <p className="text-sm text-muted-foreground mt-1">Ask your administrator to link your login to your name on the roster.</p>
      </div>
    );
  }
  if (isLoading) {
    return <div className="flex items-center justify-center py-32"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>;
  }

  const points = (data?.points || []).map((p) => ({ ...p, label: p.week_label || p.meeting_date }));
  const latest = points[points.length - 1];
  const previous = points[points.length - 2];

  const delta = (cur, prev, goodWhenDown = false) => {
    if (prev == null) return null;
    const diff = cur - prev;
    const dir = diff > 0 ? "up" : diff < 0 ? "down" : "flat";
    const good = dir === "flat" ? true : goodWhenDown ? dir === "down" : dir === "up";
    return { dir, good, text: formatINR(Math.abs(diff)) };
  };

  return (
    <div className="space-y-8" data-testid="my-performance-page">
      <div>
        <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground mb-1">My Performance</div>
        <h1 className="text-3xl font-semibold tracking-tighter">{repName}</h1>
        <p className="text-sm text-muted-foreground mt-1">Your weekly collection figures across all recorded meetings.</p>
      </div>

      {!points.length ? (
        <Card className="p-10 shadow-none text-center text-muted-foreground text-sm" data-testid="my-page-empty">
          No data recorded for you yet — your numbers will appear here after the next weekly meeting is entered.
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            <KpiCard testid="my-kpi-outstanding" label="My Outstanding" value={formatINR(latest.outstanding)}
                     sub={`as of week ${latest.label}`} icon={Wallet}
                     delta={previous ? delta(latest.outstanding, previous.outstanding, true) : null} />
            <KpiCard testid="my-kpi-collected" label="Collected This Week" value={formatINR(latest.collected)}
                     accent="success" icon={HandCoins}
                     delta={previous ? delta(latest.collected, previous.collected) : null} />
            <KpiCard testid="my-kpi-pct" label="Collection %" value={`${(latest.coll_pct || 0).toFixed(1)}%`}
                     accent={latest.coll_pct >= 12 ? "success" : latest.coll_pct >= 6 ? "warning" : "danger"}
                     sub="Collected ÷ New Target" icon={Gauge} />
          </div>

          <Card className="p-6 shadow-none">
            <h3 className="text-base font-medium mb-1">Outstanding vs Collected</h3>
            <p className="text-xs text-muted-foreground mb-5">Week by week (₹)</p>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={points}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eef0f3" />
                  <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#6B7280" }} tickLine={false} />
                  <YAxis tickFormatter={fmtAxis} tick={{ fontSize: 10, fill: "#6B7280", fontFamily: "IBM Plex Mono" }} width={92} tickLine={false} axisLine={false} />
                  <Tooltip formatter={(v) => formatINR(v)} />
                  <Legend iconType="square" wrapperStyle={{ fontSize: 12 }} />
                  <Line type="monotone" dataKey="outstanding" name="Outstanding" stroke="#141414" strokeWidth={2} dot={{ r: 3 }} />
                  <Line type="monotone" dataKey="collected" name="Collected" stroke="#16A34A" strokeWidth={2} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>

          <Card className="p-0 shadow-none overflow-hidden">
            <div className="p-6 pb-3">
              <h3 className="text-base font-medium">Weekly Detail</h3>
              <p className="text-xs text-muted-foreground mt-1">Aging buckets, outstanding and collections per week</p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-right border-collapse">
                <thead>
                  <tr className="border-y border-border bg-secondary/50 text-[10px] uppercase tracking-wider text-muted-foreground">
                    <th className="text-left px-4 py-2">Week</th>
                    {BUCKETS.map((b) => <th key={b.key} className="px-3 py-2">{b.label}</th>)}
                    <th className="px-3 py-2 bg-secondary/80">Outstanding</th>
                    <th className="px-3 py-2">Collected</th>
                    <th className="px-3 py-2">Coll %</th>
                  </tr>
                </thead>
                <tbody>
                  {[...points].reverse().map((p) => (
                    <tr key={p.label} className="border-b border-border hover:bg-secondary/30">
                      <td className="text-left px-4 py-2.5 text-sm font-medium">{p.label}</td>
                      {BUCKETS.map((b) => <td key={b.key} className="px-3 py-2.5 font-mono text-xs" style={{ color: b.color }}>{formatINR(p[b.key])}</td>)}
                      <td className="px-3 py-2.5 font-mono text-xs font-semibold bg-secondary/40">{formatINR(p.outstanding)}</td>
                      <td className="px-3 py-2.5 font-mono text-xs text-[#16A34A]">{formatINR(p.collected)}</td>
                      <td className="px-3 py-2.5 font-mono text-xs">{(p.coll_pct || 0).toFixed(1)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
