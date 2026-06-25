import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getMeetings } from "@/lib/api";
import { meetingKpis, formatINR, formatCr, COMPANY } from "@/lib/calc";
import { Card } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import CompanyToggle from "@/components/dashboard/CompanyToggle";
import { Loader2, TrendingUp } from "lucide-react";
import {
  ResponsiveContainer, AreaChart, Area, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, Legend,
} from "recharts";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function fmtShort(s) {
  if (!s) return "";
  return new Date(s).toLocaleDateString("en-IN", { day: "2-digit", month: "short" });
}

export default function Trends() {
  const { data: meetings, isLoading } = useQuery({ queryKey: ["meetings"], queryFn: getMeetings });
  const [company, setCompany] = useState(COMPANY.ALL);
  const [granularity, setGranularity] = useState("weekly");

  const series = useMemo(() => {
    if (!meetings?.length) return [];
    const sorted = [...meetings].sort((a, b) => new Date(a.meeting_date) - new Date(b.meeting_date));
    const weekly = sorted.map((m) => {
      const k = meetingKpis(m, company);
      return {
        label: fmtShort(m.period_end || m.meeting_date),
        monthKey: `${m.year}-${String(m.month).padStart(2, "0")}`,
        monthLabel: `${MONTHS[(m.month || 1) - 1]} ${m.year}`,
        outstanding: Math.round(k.totalOutstanding), collected: Math.round(k.collected),
        d90: Math.round(k.d90), d60: Math.round(k.d60), d30: Math.round(k.d30), othera: Math.round(k.othera),
        collPct: Number(k.collPct.toFixed(1)),
      };
    });
    if (granularity === "weekly") return weekly;
    const groups = {};
    weekly.forEach((w) => { (groups[w.monthKey] || (groups[w.monthKey] = { label: w.monthLabel, items: [] })).items.push(w); });
    return Object.keys(groups).sort().map((key) => {
      const g = groups[key];
      const avg = (f) => Math.round(g.items.reduce((s, x) => s + x[f], 0) / g.items.length);
      return {
        label: g.label, outstanding: avg("outstanding"), collected: avg("collected"),
        d90: avg("d90"), d60: avg("d60"), d30: avg("d30"), othera: avg("othera"),
        collPct: Number((g.items.reduce((s, x) => s + x.collPct, 0) / g.items.length).toFixed(1)),
      };
    });
  }, [meetings, company, granularity]);

  if (isLoading) return <div className="flex items-center justify-center py-32"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>;

  const curTip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    return (
      <div className="bg-white border border-border rounded-md shadow-md px-3 py-2 text-xs">
        <div className="font-semibold mb-1">{label}</div>
        {payload.map((p) => (
          <div key={p.dataKey} className="flex items-center justify-between gap-4 font-mono">
            <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-sm" style={{ background: p.color }} />{p.name}</span>
            <span>{p.dataKey === "collPct" ? `${p.value}%` : formatINR(p.value)}</span>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="space-y-8" data-testid="trends-page">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground mb-1">Performance Over Time</div>
          <h1 className="text-3xl font-semibold tracking-tighter">Trends &amp; Analytics</h1>
          <p className="text-sm text-muted-foreground mt-1">How outstanding, aging and collections move across meetings.</p>
        </div>
        <div className="flex items-center gap-3">
          <Tabs value={granularity} onValueChange={setGranularity} data-testid="granularity-toggle">
            <TabsList className="bg-secondary">
              <TabsTrigger value="weekly" data-testid="granularity-weekly">Weekly</TabsTrigger>
              <TabsTrigger value="monthly" data-testid="granularity-monthly">Monthly</TabsTrigger>
            </TabsList>
          </Tabs>
          <CompanyToggle value={company} onChange={setCompany} />
        </div>
      </div>

      <Card className="p-6 shadow-none" data-testid="trend-outstanding">
        <h3 className="text-base font-medium mb-1">Outstanding by Aging Bucket</h3>
        <p className="text-xs text-muted-foreground mb-5">Stacked outstanding over time (₹ in Crore)</p>
        <div className="h-[320px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={series} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <defs>
                {[["d30", "#2563EB"], ["d60", "#F59E0B"], ["d90", "#DC2626"], ["othera", "#6B7280"]].map(([k, c]) => (
                  <linearGradient key={k} id={`g-${k}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={c} stopOpacity={0.5} /><stop offset="100%" stopColor={c} stopOpacity={0.05} />
                  </linearGradient>
                ))}
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eef0f3" />
              <XAxis dataKey="label" tick={{ fontSize: 12, fill: "#6B7280" }} tickLine={false} axisLine={{ stroke: "#DEE2E6" }} />
              <YAxis tickFormatter={formatCr} tick={{ fontSize: 11, fill: "#6B7280", fontFamily: "IBM Plex Mono" }} tickLine={false} axisLine={false} />
              <Tooltip content={curTip} />
              <Legend iconType="square" wrapperStyle={{ fontSize: 12 }} />
              <Area type="monotone" dataKey="d30" stackId="1" name="30 Days" stroke="#2563EB" fill="url(#g-d30)" />
              <Area type="monotone" dataKey="d60" stackId="1" name="60 Days" stroke="#F59E0B" fill="url(#g-d60)" />
              <Area type="monotone" dataKey="d90" stackId="1" name="90 Days" stroke="#DC2626" fill="url(#g-d90)" />
              <Area type="monotone" dataKey="othera" stackId="1" name="Other" stroke="#6B7280" fill="url(#g-othera)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-6 shadow-none" data-testid="trend-collection">
          <h3 className="text-base font-medium mb-1">Collection Efficiency</h3>
          <p className="text-xs text-muted-foreground mb-5">Collected ÷ outstanding (%)</p>
          <div className="h-[280px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={series} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eef0f3" />
                <XAxis dataKey="label" tick={{ fontSize: 12, fill: "#6B7280" }} tickLine={false} axisLine={{ stroke: "#DEE2E6" }} />
                <YAxis unit="%" tick={{ fontSize: 11, fill: "#6B7280", fontFamily: "IBM Plex Mono" }} tickLine={false} axisLine={false} />
                <Tooltip content={curTip} />
                <Line type="monotone" dataKey="collPct" name="Collection %" stroke="#16A34A" strokeWidth={2.5} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card className="p-6 shadow-none" data-testid="trend-target">
          <h3 className="text-base font-medium mb-1">Outstanding vs Collected</h3>
          <p className="text-xs text-muted-foreground mb-5">₹ in Crore</p>
          <div className="h-[280px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={series} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eef0f3" />
                <XAxis dataKey="label" tick={{ fontSize: 12, fill: "#6B7280" }} tickLine={false} axisLine={{ stroke: "#DEE2E6" }} />
                <YAxis tickFormatter={formatCr} tick={{ fontSize: 11, fill: "#6B7280", fontFamily: "IBM Plex Mono" }} tickLine={false} axisLine={false} />
                <Tooltip content={curTip} />
                <Legend iconType="square" wrapperStyle={{ fontSize: 12 }} />
                <Line type="monotone" dataKey="outstanding" name="Outstanding" stroke="#111827" strokeWidth={2.5} dot={{ r: 3 }} />
                <Line type="monotone" dataKey="collected" name="Collected" stroke="#16A34A" strokeWidth={2} strokeDasharray="5 4" dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {series.length < 2 && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground"><TrendingUp className="h-4 w-4" /> Add more weekly meetings to see richer trends.</div>
      )}
    </div>
  );
}
