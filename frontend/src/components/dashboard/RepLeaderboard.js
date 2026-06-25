import { Card } from "@/components/ui/card";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { repRows, formatINR } from "@/lib/calc";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

function initials(name) {
  return (name || "?").split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase();
}
function pctColor(p) {
  if (p >= 12) return "text-[#16A34A]";
  if (p >= 6) return "text-[#F59E0B]";
  return "text-[#DC2626]";
}

export default function RepLeaderboard({ meeting, company }) {
  const rows = repRows(meeting, company).sort((a, b) => b.collPct - a.collPct);
  const maxOut = Math.max(...rows.map((r) => r.outstanding), 1);

  return (
    <Card className="p-6 shadow-none" data-testid="rep-leaderboard">
      <h3 className="text-base font-medium mb-1">Collection Rep Leaderboard</h3>
      <p className="text-xs text-muted-foreground mb-5">Ranked by collection efficiency this week</p>
      <div className="space-y-2">
        {rows.map((r, i) => (
          <div key={r.name} className="grid grid-cols-12 items-center gap-3 px-3 py-3 rounded-md border border-border hover:bg-secondary/50 transition-colors"
               data-testid={`leaderboard-row-${r.name}`}>
            <div className="col-span-5 sm:col-span-4 flex items-center gap-3">
              <span className="text-xs font-mono text-muted-foreground w-4">{i + 1}</span>
              <Avatar className="h-9 w-9 border border-border">
                <AvatarFallback className="bg-black text-white text-xs font-medium">{initials(r.name)}</AvatarFallback>
              </Avatar>
              <div className="min-w-0">
                <div className="text-sm font-medium truncate">{r.name}</div>
                <div className="text-[11px] text-muted-foreground font-mono">{formatINR(r.collected)} collected</div>
              </div>
            </div>
            <div className="col-span-3 sm:col-span-3">
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">Outstanding</div>
              <div className="font-mono tabular-nums text-sm">{formatINR(r.outstanding)}</div>
              <div className="mt-1 h-1.5 w-full bg-secondary rounded-full overflow-hidden">
                <div className="h-full bg-black rounded-full" style={{ width: `${(r.outstanding / maxOut) * 100}%` }} />
              </div>
            </div>
            <div className="col-span-2 sm:col-span-2 text-right sm:text-left">
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">Coll %</div>
              <div className={`font-mono tabular-nums text-sm font-semibold ${pctColor(r.collPct)}`}>{r.collPct.toFixed(1)}%</div>
            </div>
            <div className="col-span-2 sm:col-span-3 text-right">
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">WoW Outstanding</div>
              <Badge variant="outline" className={`gap-1 text-[10px] font-mono ${r.wowDelta > 0 ? "text-[#DC2626] border-[#DC2626]/30" : r.wowDelta < 0 ? "text-[#16A34A] border-[#16A34A]/30" : "text-muted-foreground"}`}>
                {r.wowDelta > 0 ? <TrendingUp className="h-3 w-3" /> : r.wowDelta < 0 ? <TrendingDown className="h-3 w-3" /> : <Minus className="h-3 w-3" />}
                {r.lastTarget ? formatINR(Math.abs(r.wowDelta)) : "—"}
              </Badge>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
