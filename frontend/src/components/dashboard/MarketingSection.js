import { Card } from "@/components/ui/card";
import { marketingRepRows } from "@/lib/calc";
import QuotationFunnel from "@/components/dashboard/QuotationFunnel";
import { Megaphone } from "lucide-react";

export default function MarketingSection({ meeting, company }) {
  const rows = marketingRepRows(meeting, company);
  const totals = rows.reduce(
    (a, r) => ({
      visit: a.visit + r.visit, inquiry: a.inquiry + r.inquiry,
      inquiryConform: a.inquiryConform + r.inquiryConform, orderLoss: a.orderLoss + r.orderLoss,
    }),
    { visit: 0, inquiry: 0, inquiryConform: 0, orderLoss: 0 }
  );
  const cols = [
    { key: "visit", label: "Visits" },
    { key: "inquiry", label: "Inquiries" },
    { key: "inquiryConform", label: "Inq. Confirmed" },
    { key: "orderLoss", label: "Order Loss" },
  ];

  return (
    <div className="grid grid-cols-1 xl:grid-cols-3 gap-6" data-testid="marketing-section">
      <div className="xl:col-span-1">
        <QuotationFunnel meeting={meeting} company={company} />
      </div>

      <Card className="p-0 shadow-none overflow-hidden xl:col-span-2">
        <div className="p-6 pb-3">
          <h3 className="text-base font-medium flex items-center gap-2"><Megaphone className="h-4 w-4" /> Marketing Activity</h3>
          <p className="text-xs text-muted-foreground mt-1">Field activity by marketing person</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-right border-collapse">
            <thead>
              <tr className="border-y border-border bg-secondary/50 text-[10px] uppercase tracking-wider text-muted-foreground">
                <th className="text-left px-4 py-2">Person</th>
                {cols.map((c) => <th key={c.key} className="px-3 py-2">{c.label}</th>)}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.name} className="border-b border-border hover:bg-secondary/30" data-testid={`marketing-row-${r.name}`}>
                  <td className="text-left px-4 py-2.5 text-sm font-medium">{r.name}</td>
                  <td className="px-3 py-2.5 font-mono text-sm">{r.visit}</td>
                  <td className="px-3 py-2.5 font-mono text-sm">{r.inquiry}</td>
                  <td className="px-3 py-2.5 font-mono text-sm text-[#16A34A]">{r.inquiryConform}</td>
                  <td className="px-3 py-2.5 font-mono text-sm text-[#DC2626]">{r.orderLoss}</td>
                </tr>
              ))}
              {!rows.length && <tr><td colSpan={5} className="text-center py-8 text-muted-foreground text-sm">No marketing data.</td></tr>}
            </tbody>
            {rows.length > 0 && (
              <tfoot>
                <tr className="border-t-2 border-black bg-secondary/60 font-semibold">
                  <td className="text-left px-4 py-2.5 text-xs uppercase tracking-wider">Total</td>
                  <td className="px-3 py-2.5 font-mono text-sm">{totals.visit}</td>
                  <td className="px-3 py-2.5 font-mono text-sm">{totals.inquiry}</td>
                  <td className="px-3 py-2.5 font-mono text-sm text-[#16A34A]">{totals.inquiryConform}</td>
                  <td className="px-3 py-2.5 font-mono text-sm text-[#DC2626]">{totals.orderLoss}</td>
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      </Card>
    </div>
  );
}
