import { useMemo, useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { getMeetings } from "@/lib/api";
import { meetingKpis, formatINR, COMPANY } from "@/lib/calc";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Loader2, Wallet, AlertOctagon, HandCoins, Gauge, CalendarRange } from "lucide-react";
import KpiCard from "@/components/dashboard/KpiCard";
import AgingChart from "@/components/dashboard/AgingChart";
import RepLeaderboard from "@/components/dashboard/RepLeaderboard";
import CollectionTable from "@/components/dashboard/CollectionTable";
import BranchSection from "@/components/dashboard/BranchSection";
import MarketingSection from "@/components/dashboard/MarketingSection";
import InsightsPanel from "@/components/dashboard/InsightsPanel";
import CompanyToggle from "@/components/dashboard/CompanyToggle";

function fmtDate(s) {
  if (!s) return "";
  return new Date(s).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

export default function Dashboard() {
  const { data: meetings, isLoading } = useQuery({ queryKey: ["meetings"], queryFn: getMeetings });
  const [params, setParams] = useSearchParams();
  const [company, setCompany] = useState(COMPANY.ALL);
  const [selectedId, setSelectedId] = useState(null);

  useEffect(() => {
    if (!meetings?.length) return;
    const fromUrl = params.get("meeting");
    if (fromUrl && meetings.some((m) => m.id === fromUrl)) setSelectedId(fromUrl);
    else setSelectedId(meetings[0].id);
  }, [meetings]); // eslint-disable-line

  const meeting = useMemo(() => meetings?.find((m) => m.id === selectedId) || meetings?.[0], [meetings, selectedId]);
  const k = useMemo(() => (meeting ? meetingKpis(meeting, company) : null), [meeting, company]);

  if (isLoading) {
    return <div className="flex items-center justify-center py-32" data-testid="dashboard-loading"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>;
  }
  if (!meetings?.length || !meeting) {
    return (
      <div className="text-center py-32" data-testid="dashboard-empty">
        <CalendarRange className="h-10 w-10 mx-auto text-muted-foreground mb-4" />
        <h2 className="text-xl font-medium">No meetings yet</h2>
        <p className="text-sm text-muted-foreground mt-1">Add your first weekly report from the Data Entry page.</p>
      </div>
    );
  }

  return (
    <div className="space-y-8" data-testid="dashboard-page">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground mb-1">Weekly Collection Meeting</div>
          <h1 className="text-3xl font-semibold tracking-tighter">Collection Insights</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Period {fmtDate(meeting.period_start)} – {fmtDate(meeting.period_end)} · {k.repCount} reps · {meeting.summary?.branch_count || 0} branches
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={meeting.id} onValueChange={(v) => { setSelectedId(v); setParams({ meeting: v }); }}>
            <SelectTrigger className="w-[240px] bg-white" data-testid="meeting-selector"><SelectValue /></SelectTrigger>
            <SelectContent>
              {meetings.map((m) => (
                <SelectItem key={m.id} value={m.id} data-testid={`meeting-option-${m.id}`}>
                  Week of {fmtDate(m.period_start)} ({m.week_label})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <CompanyToggle value={company} onChange={setCompany} />
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <KpiCard testid="kpi-total-outstanding" label="Total Outstanding" value={formatINR(k.totalOutstanding)} sub="New Target = 90+60+30+Other" icon={Wallet} delay={0} />
        <KpiCard testid="kpi-90-day" label="90-Day Overdue" value={formatINR(k.d90)} accent="danger" sub={`${(k.d90Share * 100).toFixed(0)}% of total outstanding`} icon={AlertOctagon} delay={0.06} />
        <KpiCard testid="kpi-collected" label="Collected This Week" value={formatINR(k.collected)} accent="success" sub={`${formatINR(k.collected / 6)} per day`} icon={HandCoins} delay={0.12} />
        <KpiCard testid="kpi-collection-pct" label="Collection %" value={`${k.collPct.toFixed(1)}%`} accent={k.collPct >= 12 ? "success" : k.collPct >= 6 ? "warning" : "danger"} sub="Collected ÷ outstanding" icon={Gauge} delay={0.18} />
      </div>

      <Tabs defaultValue="collection" data-testid="dashboard-tabs">
        <TabsList className="bg-secondary">
          <TabsTrigger value="collection" data-testid="tab-collection">Collection &amp; Aging</TabsTrigger>
          <TabsTrigger value="branches" data-testid="tab-branches">Sales &amp; Purchase</TabsTrigger>
          <TabsTrigger value="marketing" data-testid="tab-marketing">Marketing</TabsTrigger>
        </TabsList>

        <TabsContent value="collection" className="space-y-6 mt-6">
          <CollectionTable meeting={meeting} />
          <AgingChart meeting={meeting} company={company} />
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
            <div className="xl:col-span-2"><RepLeaderboard meeting={meeting} company={company} /></div>
            <InsightsPanel meeting={meeting} company={company} />
          </div>
        </TabsContent>

        <TabsContent value="branches" className="mt-6">
          <BranchSection meeting={meeting} company={company} />
        </TabsContent>

        <TabsContent value="marketing" className="mt-6">
          <MarketingSection meeting={meeting} company={company} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
