import { Card } from "@/components/ui/card";
import { meetingKpis, formatINR, BUCKETS } from "@/lib/calc";
import { TrendingUp } from "lucide-react";

// Week-over-week movement per aging bucket + collections.
// For dues, growth is bad (red); for collections, growth is good (green).
export default function WowStrip({ meeting, prev, company }) {
  if (!prev) return null;
  const k = meetingKpis(meeting, company);
  const pk = meetingKpis(prev, company);

  const items = [
    ...BUCKETS.map((b) => ({
      label: b.label, color: b.color,
      cur: k[b.key], diff: k[b.key] - pk[b.key], goodWhenDown: true,
    })),
    { label: "Collected", color: "#16A34A", cur: k.collected, diff: k.collected - pk.collected, goodWhenDown: false },
  ];

  return (
    <Card className="p-5 shadow-none" data-testid="wow-strip">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium flex items-center gap-2"><TrendingUp className="h-4 w-4" /> Week-over-Week Movement</h3>
        <span className="text-[11px] text-muted-foreground">vs week of {prev.week_label || prev.meeting_date}</span>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-3">
        {items.map((it) => {
          const dir = it.diff > 0 ? "up" : it.diff < 0 ? "down" : "flat";
          const good = dir === "flat" ? null : it.goodWhenDown ? dir === "down" : dir === "up";
          const color = dir === "flat" ? "text-muted-foreground" : good ? "text-[#16A34A]" : "text-[#DC2626]";
          const arrow = dir === "up" ? "▲" : dir === "down" ? "▼" : "•";
          return (
            <div key={it.label} className="rounded-md border border-border px-3 py-2.5 bg-secondary/30" data-testid={`wow-${it.label}`}>
              <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-muted-foreground">
                <span className="h-2 w-2 rounded-sm shrink-0" style={{ background: it.color }} />{it.label}
              </div>
              <div className="font-mono tabular-nums text-sm mt-1">{formatINR(it.cur)}</div>
              <div className={`font-mono tabular-nums text-xs mt-0.5 ${color}`}>
                {arrow} {formatINR(Math.abs(it.diff))}
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
