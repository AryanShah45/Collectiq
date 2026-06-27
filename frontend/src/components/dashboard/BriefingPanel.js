import { useQuery } from "@tanstack/react-query";
import { getBriefing } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Sparkles, AlertTriangle, AlertCircle, Info, Loader2, ShieldCheck } from "lucide-react";

const SEV = {
  high: { icon: AlertTriangle, cls: "text-[#DC2626]", bg: "bg-[#DC2626]/10", label: "High" },
  medium: { icon: AlertCircle, cls: "text-[#F59E0B]", bg: "bg-[#F59E0B]/10", label: "Medium" },
  low: { icon: Info, cls: "text-[#2563EB]", bg: "bg-[#2563EB]/10", label: "Low" },
};

export default function BriefingPanel({ meetingId }) {
  const { data, isLoading } = useQuery({
    queryKey: ["briefing", meetingId],
    queryFn: () => getBriefing(meetingId),
    enabled: !!meetingId,
  });

  return (
    <Card className="p-6 shadow-none" data-testid="briefing-panel">
      <div className="flex items-center gap-2 mb-3">
        <div className="h-7 w-7 rounded-md bg-black flex items-center justify-center"><Sparkles className="h-4 w-4 text-white" /></div>
        <h3 className="text-lg font-medium">Meeting Briefing</h3>
        {data?.ai && <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-secondary text-muted-foreground">AI</span>}
      </div>

      {isLoading ? (
        <div className="flex items-center gap-2 text-sm text-muted-foreground py-4"><Loader2 className="h-4 w-4 animate-spin" /> Analysing this week…</div>
      ) : (
        <>
          <p className="text-sm leading-relaxed text-foreground/90">{data?.narrative}</p>

          <div className="mt-4">
            {!data?.flags?.length ? (
              <div className="flex items-center gap-2 text-sm text-[#16A34A]"><ShieldCheck className="h-4 w-4" /> No risks flagged this week.</div>
            ) : (
              <>
                <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                  Watch list · {data.counts.high} high · {data.counts.medium} medium · {data.counts.low} low
                </div>
                <div className="space-y-2">
                  {data.flags.map((f, i) => {
                    const sev = SEV[f.severity] || SEV.low;
                    const Icon = sev.icon;
                    return (
                      <div key={i} className={`flex items-start gap-2.5 rounded-md p-2.5 ${sev.bg}`} data-testid={`flag-${i}`}>
                        <Icon className={`h-4 w-4 mt-0.5 shrink-0 ${sev.cls}`} />
                        <div>
                          <div className="text-sm font-medium">{f.title}</div>
                          <div className="text-xs text-muted-foreground">{f.detail}</div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </>
            )}
          </div>
        </>
      )}
    </Card>
  );
}
