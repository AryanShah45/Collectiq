import { Card } from "@/components/ui/card";
import { buildInsights } from "@/lib/calc";
import { AlertTriangle, AlertOctagon, CheckCircle2, Info, Lightbulb } from "lucide-react";

const styles = {
  danger: { icon: AlertOctagon, color: "#DC2626", bg: "bg-[#DC2626]/5", border: "border-[#DC2626]/20" },
  warning: { icon: AlertTriangle, color: "#F59E0B", bg: "bg-[#F59E0B]/5", border: "border-[#F59E0B]/20" },
  success: { icon: CheckCircle2, color: "#16A34A", bg: "bg-[#16A34A]/5", border: "border-[#16A34A]/20" },
  info: { icon: Info, color: "#2563EB", bg: "bg-[#2563EB]/5", border: "border-[#2563EB]/20" },
};

export default function InsightsPanel({ meeting, company }) {
  const insights = buildInsights(meeting, company);
  return (
    <Card className="p-6 shadow-none" data-testid="insights-panel">
      <div className="flex items-center gap-2 mb-1">
        <Lightbulb className="h-4 w-4" />
        <h3 className="text-base font-medium">Smart Insights</h3>
      </div>
      <p className="text-xs text-muted-foreground mb-5">Auto-generated talking points for this meeting</p>
      <div className="space-y-3">
        {insights.length === 0 && <p className="text-sm text-muted-foreground">No insights available.</p>}
        {insights.map((ins, i) => {
          const s = styles[ins.type] || styles.info;
          const Icon = s.icon;
          return (
            <div key={i} className={`flex gap-3 rounded-md border ${s.border} ${s.bg} p-3`} data-testid={`insight-${i}`}>
              <Icon className="h-4 w-4 mt-0.5 shrink-0" style={{ color: s.color }} />
              <div>
                <div className="text-sm font-medium leading-snug">{ins.title}</div>
                <div className="text-xs text-muted-foreground mt-0.5 leading-relaxed">{ins.detail}</div>
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
