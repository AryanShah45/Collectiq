import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { branchRows, formatINR, formatTons } from "@/lib/calc";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Legend,
} from "recharts";
import { Boxes } from "lucide-react";

export default function BranchSection({ meeting, company }) {
  const [metric, setMetric] = useState("value");
  const rows = branchRows(meeting, company);
  const isValue = metric === "value";

  const chartData = rows.map((b) => ({
    name: b.name,
    Purchase: isValue ? b.purchaseValue : b.purchaseTons,
    Sales: isValue ? b.salesValue : b.salesTons,
  }));

  const fmt = (v) => (isValue ? formatINR(v) : formatTons(v));
  const axisFmt = (v) => (isValue ? (v / 1e5).toFixed(0) : v.toFixed(0));

  const totals = rows.reduce(
    (a, b) => ({
      pv: a.pv + b.purchaseValue, sv: a.sv + b.salesValue,
      pt: a.pt + b.purchaseTons, st: a.st + b.salesTons,
    }),
    { pv: 0, sv: 0, pt: 0, st: 0 }
  );

  const tip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    return (
      <div className="bg-white border border-border rounded-md shadow-md px-3 py-2 text-xs">
        <div className="font-semibold mb-1">{label}</div>
        {payload.map((p) => (
          <div key={p.dataKey} className="flex items-center justify-between gap-4 font-mono">
            <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-sm" style={{ background: p.color }} />{p.name}</span>
            <span>{fmt(p.value)}</span>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="grid grid-cols-1 xl:grid-cols-3 gap-6" data-testid="branch-section">
      <Card className="p-6 shadow-none xl:col-span-2">
        <div className="flex items-center justify-between mb-1">
          <h3 className="text-base font-medium flex items-center gap-2"><Boxes className="h-4 w-4" /> Branch Sales &amp; Purchase</h3>
          <Tabs value={metric} onValueChange={setMetric}>
            <TabsList className="bg-secondary h-8">
              <TabsTrigger value="value" className="text-xs h-6" data-testid="branch-metric-value">₹ Value</TabsTrigger>
              <TabsTrigger value="tons" className="text-xs h-6" data-testid="branch-metric-tons">Tons</TabsTrigger>
            </TabsList>
          </Tabs>
        </div>
        <p className="text-xs text-muted-foreground mb-5">{isValue ? "Value in ₹ Lakh" : "Quantity in Tons"} · by branch</p>
        <div className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eef0f3" />
              <XAxis dataKey="name" tick={{ fontSize: 12, fill: "#6B7280" }} tickLine={false} axisLine={{ stroke: "#DEE2E6" }} />
              <YAxis tickFormatter={axisFmt} tick={{ fontSize: 11, fill: "#6B7280", fontFamily: "IBM Plex Mono" }} tickLine={false} axisLine={false} />
              <Tooltip content={tip} cursor={{ fill: "rgba(0,0,0,0.03)" }} />
              <Legend iconType="square" wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="Purchase" fill="#2563EB" radius={[3, 3, 0, 0]} />
              <Bar dataKey="Sales" fill="#16A34A" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <Card className="p-0 shadow-none overflow-hidden">
        <div className="p-6 pb-3"><h3 className="text-base font-medium">Branch Detail</h3>
          <p className="text-xs text-muted-foreground mt-1">Purchase &amp; Sales</p></div>
        <div className="overflow-x-auto">
          <table className="w-full text-right border-collapse">
            <thead>
              <tr className="border-y border-border bg-secondary/50 text-[10px] uppercase tracking-wider text-muted-foreground">
                <th className="text-left px-4 py-2">Branch</th>
                <th className="px-3 py-2">Purchase</th>
                <th className="px-3 py-2">Sales</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((b) => (
                <tr key={b.name} className="border-b border-border hover:bg-secondary/30" data-testid={`branch-row-${b.name}`}>
                  <td className="text-left px-4 py-2.5 text-sm font-medium">{b.name}</td>
                  <td className="px-3 py-2.5 font-mono text-xs text-[#2563EB]">{isValue ? formatINR(b.purchaseValue) : formatTons(b.purchaseTons)}</td>
                  <td className="px-3 py-2.5 font-mono text-xs text-[#16A34A]">{isValue ? formatINR(b.salesValue) : formatTons(b.salesTons)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-black bg-secondary/60 font-semibold">
                <td className="text-left px-4 py-2.5 text-xs uppercase tracking-wider">Total</td>
                <td className="px-3 py-2.5 font-mono text-xs">{isValue ? formatINR(totals.pv) : formatTons(totals.pt)}</td>
                <td className="px-3 py-2.5 font-mono text-xs">{isValue ? formatINR(totals.sv) : formatTons(totals.st)}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </Card>
    </div>
  );
}
