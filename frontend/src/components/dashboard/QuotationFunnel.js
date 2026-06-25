import { Card } from "@/components/ui/card";
import { quotationRows } from "@/lib/calc";

export default function QuotationFunnel({ meeting, company }) {
  const rows = quotationRows(meeting, company);
  const max = Math.max(...rows.map((r) => r.value), 1);
  const prepared = rows.find((r) => r.key === "prepair")?.value || 0;
  const confirmed = rows.find((r) => r.key === "conform")?.value || 0;
  const conversion = prepared ? (confirmed / prepared) * 100 : 0;

  const colors = {
    prepair: "#111827",
    conform: "#16A34A",
    pending: "#2563EB",
    under_process: "#F59E0B",
    not_conform: "#DC2626",
  };

  return (
    <Card className="p-6 shadow-none" data-testid="quotation-funnel">
      <div className="flex items-center justify-between mb-1">
        <h3 className="text-base font-medium">Quotation Pipeline</h3>
        <div className="text-right">
          <div className="font-mono tabular-nums text-lg font-semibold text-[#16A34A]">{conversion.toFixed(0)}%</div>
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Conversion</div>
        </div>
      </div>
      <p className="text-xs text-muted-foreground mb-5">Count of quotations by stage</p>
      <div className="space-y-3">
        {rows.map((r) => (
          <div key={r.key} data-testid={`quotation-stage-${r.key}`}>
            <div className="flex items-center justify-between text-sm mb-1">
              <span className="text-muted-foreground">{r.label}</span>
              <span className="font-mono tabular-nums font-medium">{r.value}</span>
            </div>
            <div className="h-2.5 w-full bg-secondary rounded-full overflow-hidden">
              <div className="h-full rounded-full transition-all duration-500"
                   style={{ width: `${(r.value / max) * 100}%`, background: colors[r.key] }} />
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
