export const COMPANY = { ALL: "all", MBS: "mbs", MCORP: "mcorp" };

export const BUCKETS = [
  { key: "d90", label: "90 Days", short: "90d", color: "#DC2626" },
  { key: "d60", label: "60 Days", short: "60d", color: "#F59E0B" },
  { key: "d30", label: "30 Days", short: "30d", color: "#2563EB" },
  { key: "othera", label: "Other", short: "Other", color: "#6B7280" },
];

export function amt(a, company) {
  if (!a) return 0;
  if (company === COMPANY.MBS) return a.mbs || 0;
  if (company === COMPANY.MCORP) return a.mcorp || 0;
  return (a.mbs || 0) + (a.mcorp || 0);
}

export function formatINR(n) {
  const v = Number(n) || 0;
  const sign = v < 0 ? "-" : "";
  const x = Math.abs(v);
  if (x >= 1e7) return `${sign}₹${(x / 1e7).toFixed(2)} Cr`;
  if (x >= 1e5) return `${sign}₹${(x / 1e5).toFixed(2)} L`;
  if (x >= 1e3) return `${sign}₹${(x / 1e3).toFixed(1)}K`;
  return `${sign}₹${x.toFixed(0)}`;
}

export function formatCr(n) {
  const v = Number(n) || 0;
  return (v / 1e7).toFixed(1);
}

export function formatNum(n) {
  return (Number(n) || 0).toLocaleString("en-IN");
}

export function meetingKpis(meeting, company) {
  const reps = meeting?.reps || [];
  let d90 = 0, d60 = 0, d30 = 0, othera = 0;
  let totalNewTarget = 0, totalLastTarget = 0, totalCollPerDay = 0;
  const pcts = [];
  reps.forEach((r) => {
    const ag = r.aging || {};
    d90 += amt(ag.d90, company);
    d60 += amt(ag.d60, company);
    d30 += amt(ag.d30, company);
    othera += amt(ag.othera, company);
    const p = r.performance || {};
    totalNewTarget += p.new_target || 0;
    totalLastTarget += p.last_week_target || 0;
    totalCollPerDay += p.coll_per_day || 0;
    if (p.coll_pct) pcts.push(p.coll_pct);
  });
  const totalOutstanding = d90 + d60 + d30 + othera;
  return {
    totalOutstanding, d90, d60, d30, othera,
    totalNewTarget, totalLastTarget, totalCollPerDay,
    avgCollPct: pcts.length ? pcts.reduce((a, b) => a + b, 0) / pcts.length : 0,
    repCount: reps.length,
    d90Share: totalOutstanding ? d90 / totalOutstanding : 0,
  };
}

export function repRows(meeting, company) {
  return (meeting?.reps || []).map((r) => {
    const ag = r.aging || {};
    const p = r.performance || {};
    const outstanding = amt(ag.d90, company) + amt(ag.d60, company) + amt(ag.d30, company) + amt(ag.othera, company);
    return {
      name: r.name,
      d90: amt(ag.d90, company),
      d60: amt(ag.d60, company),
      d30: amt(ag.d30, company),
      othera: amt(ag.othera, company),
      outstanding,
      collPct: p.coll_pct || 0,
      collPerDay: p.coll_per_day || 0,
      newTarget: p.new_target || 0,
      lastTarget: p.last_week_target || 0,
      targetDelta: (p.new_target || 0) - (p.last_week_target || 0),
    };
  });
}

export function quotationRows(meeting, company) {
  const q = meeting?.quotation || {};
  const stages = [
    { key: "prepair", label: "Prepared" },
    { key: "conform", label: "Confirmed" },
    { key: "pending", label: "Pending" },
    { key: "under_process", label: "Under Process" },
    { key: "not_conform", label: "Not Confirmed" },
  ];
  return stages.map((s) => ({ ...s, value: amt(q[s.key], company) }));
}

export function buildInsights(meeting, company) {
  const k = meetingKpis(meeting, company);
  const reps = repRows(meeting, company);
  const q = quotationRows(meeting, company);
  const insights = [];
  if (!reps.length) return insights;

  // 90-day risk concentration
  if (k.d90Share > 0.25) {
    insights.push({
      type: "danger",
      title: "High 90+ day exposure",
      detail: `${(k.d90Share * 100).toFixed(0)}% of all outstanding (${formatINR(k.d90)}) is stuck in the 90-day bucket — prioritise recovery.`,
    });
  }

  // worst 90-day holder
  const worst90 = [...reps].sort((a, b) => b.d90 - a.d90)[0];
  if (worst90 && worst90.d90 > 0) {
    insights.push({
      type: "info",
      title: `${worst90.name} holds the largest 90-day overdue`,
      detail: `${formatINR(worst90.d90)} ageing beyond 90 days — needs a dedicated follow-up plan.`,
    });
  }

  // low collection % reps
  const low = reps.filter((r) => r.collPct > 0 && r.collPct < 15).sort((a, b) => a.collPct - b.collPct);
  low.slice(0, 2).forEach((r) => {
    insights.push({
      type: "warning",
      title: `${r.name}'s collection efficiency is low`,
      detail: `Collection at ${r.collPct.toFixed(1)}% against a target of ${formatINR(r.newTarget)}.`,
    });
  });

  // best performer
  const best = [...reps].sort((a, b) => b.collPct - a.collPct)[0];
  if (best && best.collPct > 0) {
    insights.push({
      type: "success",
      title: `${best.name} leads on collections`,
      detail: `Top collection efficiency at ${best.collPct.toFixed(1)}% — share the playbook with the team.`,
    });
  }

  // target movement
  const delta = k.totalNewTarget - k.totalLastTarget;
  if (Math.abs(delta) > 0) {
    insights.push({
      type: delta > 0 ? "warning" : "info",
      title: delta > 0 ? "Targets increased this week" : "Targets eased this week",
      detail: `Total target moved ${delta > 0 ? "up" : "down"} by ${formatINR(Math.abs(delta))} vs last week (now ${formatINR(k.totalNewTarget)}).`,
    });
  }

  // quotation conversion
  const prep = q.find((s) => s.key === "prepair")?.value || 0;
  const conf = q.find((s) => s.key === "conform")?.value || 0;
  if (prep > 0) {
    const conv = (conf / prep) * 100;
    insights.push({
      type: conv < 60 ? "warning" : "success",
      title: "Quotation conversion",
      detail: `${conf} of ${prep} quotations confirmed (${conv.toFixed(0)}% conversion).`,
    });
  }

  return insights;
}

export function emptyRep(name = "") {
  const z = () => ({ mbs: 0, mcorp: 0 });
  return {
    name,
    aging: { d90: z(), d60: z(), d30: z(), othera: z() },
    performance: {
      purchase: z(), sales: z(),
      coll_per_day: 0, coll_pct: 0, new_target: 0, last_week_target: 0,
    },
  };
}

export function emptyQuotation() {
  const z = () => ({ mbs: 0, mcorp: 0 });
  return { prepair: z(), conform: z(), pending: z(), under_process: z(), not_conform: z() };
}
