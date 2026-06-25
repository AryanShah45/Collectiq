import { Card } from "@/components/ui/card";
import { repRows, BUCKETS, formatINR, formatCr } from "@/lib/calc";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend, CartesianGrid, Cell,
  PieChart, Pie,
} from "recharts";

function CurrencyTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const total = payload.reduce((s, p) => s + (p.value || 0), 0);
  return (
    <div className="bg-white border border-border rounded-md shadow-md px-3 py-2 text-xs">
      <div className="font-semibold mb-1">{label}</div>
      {payload.map((p) => (
        <div key={p.dataKey} className="flex items-center justify-between gap-4 font-mono">
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-sm" style={{ background: p.color }} />
            {p.name}
          </span>
          <span>{formatINR(p.value)}</span>
        </div>
      ))}
      <div className="flex items-center justify-between gap-4 mt-1 pt-1 border-t border-border font-mono font-semibold">
        <span>Total</span><span>{formatINR(total)}</span>
      </div>
    </div>
  );
}

export default function AgingChart({ meeting, company }) {
  const rows = repRows(meeting, company);
  const data = rows.map((r) => ({
    name: r.name, d90: r.d90, d60: r.d60, d30: r.d30, othera: r.othera,
  }));
  const pieData = BUCKETS.map((b) => ({
    name: b.label, value: rows.reduce((s, r) => s + r[b.key], 0), color: b.color,
  })).filter((d) => d.value > 0);

  return (
    <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
      <Card className="p-6 xl:col-span-2 shadow-none" data-testid="aging-bar-chart">
        <div className="flex items-center justify-between mb-1">
          <h3 className="text-base font-medium">Accounts Receivable Aging by Representative</h3>
        </div>
        <p className="text-xs text-muted-foreground mb-5">Outstanding split across aging buckets (₹ in Crore)</p>
        <div className="h-[340px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eef0f3" />
              <XAxis dataKey="name" tick={{ fontSize: 12, fill: "#6B7280" }} tickLine={false} axisLine={{ stroke: "#DEE2E6" }} />
              <YAxis tickFormatter={formatCr} tick={{ fontSize: 11, fill: "#6B7280", fontFamily: "IBM Plex Mono" }} tickLine={false} axisLine={false} />
              <Tooltip content={<CurrencyTooltip />} cursor={{ fill: "rgba(0,0,0,0.03)" }} />
              <Legend iconType="square" wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="d30" stackId="a" name="30 Days" fill="#2563EB" />
              <Bar dataKey="d60" stackId="a" name="60 Days" fill="#F59E0B" />
              <Bar dataKey="d90" stackId="a" name="90 Days" fill="#DC2626" />
              <Bar dataKey="othera" stackId="a" name="Other" fill="#6B7280" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <Card className="p-6 shadow-none" data-testid="aging-composition-chart">
        <h3 className="text-base font-medium mb-1">Aging Composition</h3>
        <p className="text-xs text-muted-foreground mb-2">Where the money is stuck</p>
        <div className="h-[230px]">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={85} paddingAngle={2}>
                {pieData.map((d) => <Cell key={d.name} fill={d.color} />)}
              </Pie>
              <Tooltip formatter={(v, n) => [formatINR(v), n]} />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="space-y-2 mt-2">
          {pieData.map((d) => (
            <div key={d.name} className="flex items-center justify-between text-sm">
              <span className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-sm" style={{ background: d.color }} />
                {d.name}
              </span>
              <span className="font-mono tabular-nums">{formatINR(d.value)}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
