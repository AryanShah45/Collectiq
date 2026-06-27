import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getMeetings, downloadTrendsReport } from "@/lib/api";
import { meetingKpis, amt, formatINR, formatCr, COMPANY } from "@/lib/calc";
import { Card } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import CompanyToggle from "@/components/dashboard/CompanyToggle";
import { Loader2, TrendingUp, FileText, Wallet, ShoppingCart, Megaphone, BarChart3 } from "lucide-react";
import { toast } from "sonner";
import {
  ResponsiveContainer, AreaChart, Area, LineChart, Line, BarChart, Bar,
  XAxis, YAxis, Tooltip, CartesianGrid, Legend,
} from "recharts";

function fmtShort(s) {
  if (!s) return "";
  return new Date(s).toLocaleDateString("en-IN", { day: "2-digit", month: "short" });
}

const DEPTS = [
  { id: "collection", label: "Collection", icon: Wallet },
  { id: "sales", label: "Sales vs Purchase", icon: ShoppingCart },
  { id: "marketing", label: "Marketing", icon: Megaphone },
  { id: "analysis", label: "Analysis", icon: BarChart3 },
];

const moneyTip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-border rounded-md shadow-md px-3 py-2 text-xs">
      <div className="font-semibold mb-1">{label}</div>
      {payload.map((p) => (
        <div key={p.dataKey} className="flex items-center justify-between gap-4 font-mono">
          <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-sm" style={{ background: p.color }} />{p.name}</span>
          <span>{String(p.dataKey).includes("pct") || String(p.dataKey).includes("conv") ? `${p.value}%`
            : String(p.dataKey).includes("Tons") || ["visits", "inquiries", "confirmed", "orderLoss"].includes(p.dataKey) ? p.value
            : formatINR(p.value)}</span>
        </div>
      ))}
    </div>
  );
};

const axis = { tick: { fontSize: 11, fill: "#6B7280" }, tickLine: false, axisLine: { stroke: "#DEE2E6" } };

export default function Trends() {
  const { data: meetings, isLoading } = useQuery({ queryKey: ["meetings"], queryFn: getMeetings });
  const [company, setCompany] = useState(COMPANY.ALL);
  const [dept, setDept] = useState("collection");
  const [downloading, setDownloading] = useState(false);

  const { series, branchNames, branchSeries } = useMemo(() => {
    if (!meetings?.length) return { series: [], branchNames: [], branchSeries: [] };
    const sorted = [...meetings].sort((a, b) => new Date(a.meeting_date) - new Date(b.meeting_date));
    const names = new Set();
    const series = sorted.map((m) => {
      const k = meetingKpis(m, company);
      let salesTons = 0, purchaseTons = 0, salesValB = 0, purchaseValB = 0;
      const branchMap = {};
      (m.branches || []).forEach((b) => {
        const st = amt(b.sales?.tons, company), pt = amt(b.purchase?.tons, company);
        salesTons += st; purchaseTons += pt;
        salesValB += amt(b.sales?.value, company); purchaseValB += amt(b.purchase?.value, company);
        names.add(b.name);
        branchMap[b.name] = { salesTons: st, purchaseTons: pt };
      });
      const salesValue = amt(m.financials?.sales_value, company) || salesValB;
      const purchaseValue = amt(m.financials?.purchase_value, company) || purchaseValB;
      let visits = 0, inquiries = 0, confirmed = 0, orderLoss = 0;
      (m.marketing_reps || []).forEach((mr) => {
        visits += amt(mr.visit, company); inquiries += amt(mr.inquiry, company);
        confirmed += amt(mr.inquiry_conform, company); orderLoss += amt(mr.order_loss, company);
      });
      const q = m.quotation || {};
      return {
        label: fmtShort(m.period_end || m.meeting_date), date: m.meeting_date,
        outstanding: Math.round(k.totalOutstanding), collected: Math.round(k.collected),
        d90: Math.round(k.d90), d60: Math.round(k.d60), d30: Math.round(k.d30), othera: Math.round(k.othera),
        collPct: Number(k.collPct.toFixed(1)),
        salesValue: Math.round(salesValue), purchaseValue: Math.round(purchaseValue),
        netValue: Math.round(salesValue - purchaseValue),
        salesTons: Number(salesTons.toFixed(2)), purchaseTons: Number(purchaseTons.toFixed(2)),
        visits, inquiries, confirmed, orderLoss,
        conv: inquiries ? Number((confirmed / inquiries * 100).toFixed(1)) : 0,
        qPrepared: amt(q.prepair, company), qConfirmed: amt(q.conform, company), qPending: amt(q.pending, company),
        qUnder: amt(q.under_process, company), qNot: amt(q.not_conform, company),
        branchMap,
      };
    });
    const branchNames = [...names];
    const branchSeries = series.map((s) => {
      const row = { label: s.label };
      branchNames.forEach((n) => { row[`s_${n}`] = s.branchMap[n]?.salesTons || 0; row[`p_${n}`] = s.branchMap[n]?.purchaseTons || 0; });
      return row;
    });
    return { series, branchNames, branchSeries };
  }, [meetings, company]);

  const downloadReport = async () => {
    setDownloading(true);
    try {
      const blob = await downloadTrendsReport();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = "collectiq-trends-report.pdf";
      document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
      toast.success("Report downloaded");
    } catch { toast.error("Could not generate report"); }
    finally { setDownloading(false); }
  };

  if (isLoading) return <div className="flex items-center justify-center py-32"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>;

  const latest = series[series.length - 1];
  const BRANCH_COLORS = ["#111827", "#2563EB", "#16A34A", "#F59E0B", "#DC2626", "#7C3AED", "#0891B2", "#DB2777"];

  return (
    <div className="space-y-6" data-testid="trends-page">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground mb-1">Performance Over Time</div>
          <h1 className="text-3xl font-semibold tracking-tighter">Trends &amp; Analytics</h1>
          <p className="text-sm text-muted-foreground mt-1">Department-wise analysis across all your weekly meetings.</p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={downloadReport} disabled={downloading} data-testid="download-trends-report">
            {downloading ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileText className="h-4 w-4" />} Download Report (PDF)
          </Button>
          <CompanyToggle value={company} onChange={setCompany} />
        </div>
      </div>

      {/* Department tabs */}
      <div className="flex flex-wrap gap-2">
        {DEPTS.map((d) => {
          const Icon = d.icon;
          return (
            <button key={d.id} onClick={() => setDept(d.id)} data-testid={`dept-${d.id}`}
              className={`inline-flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium border transition-colors ${dept === d.id ? "bg-black text-white border-black" : "bg-white text-muted-foreground border-border hover:bg-secondary"}`}>
              <Icon className="h-4 w-4" /> {d.label}
            </button>
          );
        })}
      </div>

      {!series.length ? (
        <div className="flex items-center gap-2 text-sm text-muted-foreground py-12"><TrendingUp className="h-4 w-4" /> No meetings yet — add weekly data to see analytics.</div>
      ) : (
        <>
          {/* ===================== COLLECTION ===================== */}
          {dept === "collection" && (
            <div className="space-y-6">
              <Card className="p-6 shadow-none">
                <h3 className="text-base font-medium mb-1">Outstanding by Aging Bucket</h3>
                <p className="text-xs text-muted-foreground mb-5">Stacked outstanding over time (₹ in Crore)</p>
                <div className="h-[320px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={series} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                      <defs>
                        {[["d30", "#2563EB"], ["d60", "#F59E0B"], ["d90", "#DC2626"], ["othera", "#6B7280"]].map(([k, c]) => (
                          <linearGradient key={k} id={`g-${k}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={c} stopOpacity={0.5} /><stop offset="100%" stopColor={c} stopOpacity={0.05} /></linearGradient>
                        ))}
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eef0f3" />
                      <XAxis dataKey="label" {...axis} /><YAxis tickFormatter={formatCr} {...axis} />
                      <Tooltip content={moneyTip} /><Legend iconType="square" wrapperStyle={{ fontSize: 12 }} />
                      <Area type="monotone" dataKey="d30" stackId="1" name="30 Days" stroke="#2563EB" fill="url(#g-d30)" />
                      <Area type="monotone" dataKey="d60" stackId="1" name="60 Days" stroke="#F59E0B" fill="url(#g-d60)" />
                      <Area type="monotone" dataKey="d90" stackId="1" name="90 Days" stroke="#DC2626" fill="url(#g-d90)" />
                      <Area type="monotone" dataKey="othera" stackId="1" name="Other" stroke="#6B7280" fill="url(#g-othera)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </Card>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card className="p-6 shadow-none">
                  <h3 className="text-base font-medium mb-1">Collection Efficiency</h3>
                  <p className="text-xs text-muted-foreground mb-5">Collected ÷ target (%)</p>
                  <div className="h-[280px]"><ResponsiveContainer width="100%" height="100%">
                    <LineChart data={series}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eef0f3" /><XAxis dataKey="label" {...axis} /><YAxis unit="%" {...axis} /><Tooltip content={moneyTip} />
                      <Line type="monotone" dataKey="collPct" name="Collection %" stroke="#16A34A" strokeWidth={2.5} dot={{ r: 3 }} /></LineChart>
                  </ResponsiveContainer></div>
                </Card>
                <Card className="p-6 shadow-none">
                  <h3 className="text-base font-medium mb-1">Outstanding vs Collected</h3>
                  <p className="text-xs text-muted-foreground mb-5">₹ in Crore</p>
                  <div className="h-[280px]"><ResponsiveContainer width="100%" height="100%">
                    <LineChart data={series}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eef0f3" /><XAxis dataKey="label" {...axis} /><YAxis tickFormatter={formatCr} {...axis} /><Tooltip content={moneyTip} /><Legend iconType="square" wrapperStyle={{ fontSize: 12 }} />
                      <Line type="monotone" dataKey="outstanding" name="Outstanding" stroke="#111827" strokeWidth={2.5} dot={{ r: 3 }} />
                      <Line type="monotone" dataKey="collected" name="Collected" stroke="#16A34A" strokeWidth={2} strokeDasharray="5 4" dot={{ r: 3 }} /></LineChart>
                  </ResponsiveContainer></div>
                </Card>
              </div>
            </div>
          )}

          {/* ===================== SALES vs PURCHASE ===================== */}
          {dept === "sales" && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card className="p-6 shadow-none">
                  <h3 className="text-base font-medium mb-1">Sales vs Purchase (Value)</h3>
                  <p className="text-xs text-muted-foreground mb-5">₹ in Crore over time</p>
                  <div className="h-[300px]"><ResponsiveContainer width="100%" height="100%">
                    <LineChart data={series}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eef0f3" /><XAxis dataKey="label" {...axis} /><YAxis tickFormatter={formatCr} {...axis} /><Tooltip content={moneyTip} /><Legend iconType="square" wrapperStyle={{ fontSize: 12 }} />
                      <Line type="monotone" dataKey="salesValue" name="Sales" stroke="#16A34A" strokeWidth={2.5} dot={{ r: 3 }} />
                      <Line type="monotone" dataKey="purchaseValue" name="Purchase" stroke="#DC2626" strokeWidth={2.5} dot={{ r: 3 }} /></LineChart>
                  </ResponsiveContainer></div>
                </Card>
                <Card className="p-6 shadow-none">
                  <h3 className="text-base font-medium mb-1">Sales vs Purchase (Tonnage)</h3>
                  <p className="text-xs text-muted-foreground mb-5">Tons over time</p>
                  <div className="h-[300px]"><ResponsiveContainer width="100%" height="100%">
                    <LineChart data={series}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eef0f3" /><XAxis dataKey="label" {...axis} /><YAxis {...axis} /><Tooltip content={moneyTip} /><Legend iconType="square" wrapperStyle={{ fontSize: 12 }} />
                      <Line type="monotone" dataKey="salesTons" name="Sales (T)" stroke="#16A34A" strokeWidth={2.5} dot={{ r: 3 }} />
                      <Line type="monotone" dataKey="purchaseTons" name="Purchase (T)" stroke="#DC2626" strokeWidth={2.5} dot={{ r: 3 }} /></LineChart>
                  </ResponsiveContainer></div>
                </Card>
              </div>
              <Card className="p-6 shadow-none">
                <h3 className="text-base font-medium mb-1">Branchwise Sales (Tonnage)</h3>
                <p className="text-xs text-muted-foreground mb-5">Each branch's sales tons over time</p>
                <div className="h-[320px]"><ResponsiveContainer width="100%" height="100%">
                  <LineChart data={branchSeries}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eef0f3" /><XAxis dataKey="label" {...axis} /><YAxis {...axis} /><Tooltip /><Legend iconType="square" wrapperStyle={{ fontSize: 12 }} />
                    {branchNames.map((n, i) => <Line key={n} type="monotone" dataKey={`s_${n}`} name={n} stroke={BRANCH_COLORS[i % BRANCH_COLORS.length]} strokeWidth={2} dot={{ r: 2 }} />)}
                  </LineChart>
                </ResponsiveContainer></div>
              </Card>
              {latest && (
                <Card className="p-6 shadow-none">
                  <h3 className="text-base font-medium mb-1">Branchwise — Latest Week ({latest.date})</h3>
                  <p className="text-xs text-muted-foreground mb-5">Sales vs Purchase tonnage per branch</p>
                  <div className="h-[300px]"><ResponsiveContainer width="100%" height="100%">
                    <BarChart data={branchNames.map((n) => ({ name: n, sales: latest.branchMap[n]?.salesTons || 0, purchase: latest.branchMap[n]?.purchaseTons || 0 }))}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eef0f3" /><XAxis dataKey="name" {...axis} /><YAxis {...axis} /><Tooltip /><Legend iconType="square" wrapperStyle={{ fontSize: 12 }} />
                      <Bar dataKey="sales" name="Sales (T)" fill="#16A34A" radius={[3, 3, 0, 0]} /><Bar dataKey="purchase" name="Purchase (T)" fill="#DC2626" radius={[3, 3, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer></div>
                </Card>
              )}
            </div>
          )}

          {/* ===================== MARKETING ===================== */}
          {dept === "marketing" && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card className="p-6 shadow-none">
                  <h3 className="text-base font-medium mb-1">Visits & Inquiries</h3>
                  <p className="text-xs text-muted-foreground mb-5">Marketing activity over time</p>
                  <div className="h-[290px]"><ResponsiveContainer width="100%" height="100%">
                    <LineChart data={series}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eef0f3" /><XAxis dataKey="label" {...axis} /><YAxis {...axis} /><Tooltip content={moneyTip} /><Legend iconType="square" wrapperStyle={{ fontSize: 12 }} />
                      <Line type="monotone" dataKey="visits" name="Visits" stroke="#2563EB" strokeWidth={2.5} dot={{ r: 3 }} />
                      <Line type="monotone" dataKey="inquiries" name="Inquiries" stroke="#F59E0B" strokeWidth={2.5} dot={{ r: 3 }} />
                      <Line type="monotone" dataKey="confirmed" name="Confirmed" stroke="#16A34A" strokeWidth={2.5} dot={{ r: 3 }} /></LineChart>
                  </ResponsiveContainer></div>
                </Card>
                <Card className="p-6 shadow-none">
                  <h3 className="text-base font-medium mb-1">Conversion Rate</h3>
                  <p className="text-xs text-muted-foreground mb-5">Confirmed ÷ inquiries (%)</p>
                  <div className="h-[290px]"><ResponsiveContainer width="100%" height="100%">
                    <LineChart data={series}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eef0f3" /><XAxis dataKey="label" {...axis} /><YAxis unit="%" {...axis} /><Tooltip content={moneyTip} />
                      <Line type="monotone" dataKey="conv" name="Conversion %" stroke="#7C3AED" strokeWidth={2.5} dot={{ r: 3 }} /></LineChart>
                  </ResponsiveContainer></div>
                </Card>
              </div>
              {latest && (
                <Card className="p-6 shadow-none">
                  <h3 className="text-base font-medium mb-1">Quotation Funnel — Latest Week ({latest.date})</h3>
                  <p className="text-xs text-muted-foreground mb-5">Pipeline stage counts</p>
                  <div className="h-[300px]"><ResponsiveContainer width="100%" height="100%">
                    <BarChart data={[
                      { stage: "Prepared", v: latest.qPrepared }, { stage: "Confirmed", v: latest.qConfirmed },
                      { stage: "Pending", v: latest.qPending }, { stage: "Under Process", v: latest.qUnder }, { stage: "Not Confirmed", v: latest.qNot },
                    ]}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eef0f3" /><XAxis dataKey="stage" {...axis} /><YAxis {...axis} /><Tooltip />
                      <Bar dataKey="v" name="Quotations" fill="#111827" radius={[3, 3, 0, 0]} /></BarChart>
                  </ResponsiveContainer></div>
                </Card>
              )}
            </div>
          )}

          {/* ===================== ANALYSIS ===================== */}
          {dept === "analysis" && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                {(() => {
                  const n = series.length;
                  const avgPct = (series.reduce((s, w) => s + w.collPct, 0) / n).toFixed(1);
                  const totColl = series.reduce((s, w) => s + w.collected, 0);
                  const totSales = series.reduce((s, w) => s + w.salesValue, 0);
                  const totPurch = series.reduce((s, w) => s + w.purchaseValue, 0);
                  const cards = [
                    { label: "Avg Collection %", value: `${avgPct}%` },
                    { label: "Total Collected", value: formatINR(totColl) },
                    { label: "Total Sales", value: formatINR(totSales) },
                    { label: "Net (Sales−Purchase)", value: formatINR(totSales - totPurch) },
                  ];
                  return cards.map((c) => (
                    <Card key={c.label} className="p-4 shadow-none">
                      <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">{c.label}</div>
                      <div className="text-xl font-semibold font-mono tabular-nums">{c.value}</div>
                    </Card>
                  ));
                })()}
              </div>
              <Card className="p-6 shadow-none">
                <h3 className="text-base font-medium mb-1">Collection % vs Sales Value</h3>
                <p className="text-xs text-muted-foreground mb-5">Does collection efficiency track sales? (dual axis)</p>
                <div className="h-[320px]"><ResponsiveContainer width="100%" height="100%">
                  <LineChart data={series}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eef0f3" /><XAxis dataKey="label" {...axis} />
                    <YAxis yAxisId="l" unit="%" {...axis} /><YAxis yAxisId="r" orientation="right" tickFormatter={formatCr} {...axis} /><Tooltip content={moneyTip} /><Legend iconType="square" wrapperStyle={{ fontSize: 12 }} />
                    <Line yAxisId="l" type="monotone" dataKey="collPct" name="Collection %" stroke="#16A34A" strokeWidth={2.5} dot={{ r: 3 }} />
                    <Line yAxisId="r" type="monotone" dataKey="salesValue" name="Sales" stroke="#2563EB" strokeWidth={2} strokeDasharray="5 4" dot={{ r: 3 }} /></LineChart>
                </ResponsiveContainer></div>
              </Card>
              <Card className="p-6 shadow-none">
                <h3 className="text-base font-medium mb-1">Net Sales − Purchase Position</h3>
                <p className="text-xs text-muted-foreground mb-5">Weekly net (₹ in Crore)</p>
                <div className="h-[280px]"><ResponsiveContainer width="100%" height="100%">
                  <BarChart data={series}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eef0f3" /><XAxis dataKey="label" {...axis} /><YAxis tickFormatter={formatCr} {...axis} /><Tooltip content={moneyTip} />
                    <Bar dataKey="netValue" name="Net" radius={[3, 3, 0, 0]} fill="#111827" /></BarChart>
                </ResponsiveContainer></div>
              </Card>
            </div>
          )}
        </>
      )}
    </div>
  );
}
