import { motion } from "framer-motion";
import { Card } from "@/components/ui/card";

export default function KpiCard({ label, value, sub, accent = "default", icon: Icon, delay = 0, testid }) {
  const accents = {
    default: "text-foreground",
    danger: "text-[#DC2626]",
    warning: "text-[#F59E0B]",
    info: "text-[#2563EB]",
    success: "text-[#16A34A]",
  };
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay, ease: "easeOut" }}
    >
      <Card className="p-5 border-border shadow-none hover:shadow-sm hover:-translate-y-0.5 transition-all duration-200" data-testid={testid}>
        <div className="flex items-start justify-between">
          <span className="text-[11px] font-semibold uppercase tracking-[0.15em] text-muted-foreground">{label}</span>
          {Icon && <Icon className={`h-4 w-4 ${accents[accent]}`} />}
        </div>
        <div className={`mt-3 font-mono tabular-nums text-2xl lg:text-3xl tracking-tight ${accents[accent]}`}>{value}</div>
        {sub && <div className="mt-1.5 text-xs text-muted-foreground">{sub}</div>}
      </Card>
    </motion.div>
  );
}
