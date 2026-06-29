export const COMPANY = { ALL: "all", MBS: "mbs", MCORP: "mcorp" };

export const BUCKETS = [
  { key: "d90", label: "90 Days", short: "90d", color: "#DC2626" },
  { key: "d60", label: "60 Days", short: "60d", color: "#F59E0B" },
  { key: "d30", label: "30 Days", short: "30d", color: "#2563EB" },
  { key: "d15", label: "15 Days", short: "15d", color: "#0EA5E9", mcorpOnly: true },
  { key: "othera", label: "Other", short: "Other", color: "#6B7280" },
];

// Fixed working days used for all per-day calculations (collection/day, sale/day).
export const WORKING_DAYS = 6;

export function amt(a, company) {
  if (!a) return 0;
  if (typeof a === "number") return company === COMPANY.ALL || !company ? a : 0;
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

export const formatCr = (n) => ((Number(n) || 0) / 1e7).toFixed(1);
export const formatNum = (n) => (Number(n) || 0).toLocaleString("en-IN");
export const formatTons = (n) => `${(Number(n) || 0).toFixed(2)} T`;

export function meetingKpis(meeting, company) {
  const reps = meeting?.reps || [];
  let d90 = 0, d60 = 0, d30 = 0, d15 = 0, othera = 0, collected = 0;
  reps.forEach((r) => {
    const ag = r.aging || {};
    d90 += amt(ag.d90, company);
    d60 += amt(ag.d60, company);
    d30 += amt(ag.d30, company);
    d15 += amt(ag.d15, company);
    othera += amt(ag.othera, company);
    collected += amt(r.weekly_collection, company);
  });
  const totalOutstanding = d90 + d60 + d30 + d15 + othera;
  // NEW TARGET = (MBS 90+60+30) + (MCORP 90+60+30+15). d15 is MCORP-only so the
  // MBS side is always 0. Excludes the OTHER bucket.
  const newTarget = d90 + d60 + d30 + d15;
  return {
    totalOutstanding, d90, d60, d30, d15, othera,
    collected,
    collPerDay: collected / WORKING_DAYS,
    collPct: newTarget ? (collected / newTarget) * 100 : 0,
    newTarget,
    repCount: reps.length,
    d90Share: totalOutstanding ? d90 / totalOutstanding : 0,
  };
}

export function repRows(meeting, company) {
  return (meeting?.reps || []).map((r) => {
    const ag = r.aging || {};
    const d90 = amt(ag.d90, company), d60 = amt(ag.d60, company);
    const d30 = amt(ag.d30, company), d15 = amt(ag.d15, company), othera = amt(ag.othera, company);
    const outstanding = d90 + d60 + d30 + d15 + othera;
    const newTarget = d90 + d60 + d30 + d15; // (MBS 90+60+30) + (MCORP 90+60+30+15); excludes OTHER
    const collected = amt(r.weekly_collection, company);
    const collectedMbs = amt(r.weekly_collection, "mbs");
    const collectedMcorp = amt(r.weekly_collection, "mcorp");
    const wd = r.working_days || WORKING_DAYS;
    const lastTarget = r.last_week_target || 0;
    return {
      name: r.name, d90, d60, d30, d15, othera, outstanding,
      mbs: amt(ag.d90, "mbs") + amt(ag.d60, "mbs") + amt(ag.d30, "mbs") + amt(ag.d15, "mbs") + amt(ag.othera, "mbs"),
      mcorp: amt(ag.d90, "mcorp") + amt(ag.d60, "mcorp") + amt(ag.d30, "mcorp") + amt(ag.d15, "mcorp") + amt(ag.othera, "mcorp"),
      collected, collectedMbs, collectedMcorp,
      collPerDay: collected / wd,
      collPct: newTarget ? (collected / newTarget) * 100 : 0,
      newTarget,
      lastTarget,
      wowDelta: newTarget - lastTarget,
    };
  });
}

export function bucketCell(rep, bucketKey) {
  const a = (rep.aging || {})[bucketKey] || {};
  return { mbs: a.mbs || 0, mcorp: a.mcorp || 0, total: (a.mbs || 0) + (a.mcorp || 0) };
}

export function branchRows(meeting, company) {
  return (meeting?.branches || []).map((b) => {
    const purchaseTons = amt(b.purchase?.tons, company);
    const salesTons = amt(b.sales?.tons, company);
    return {
      name: b.name,
      purchaseTons,
      salesTons,
      purchasePerDay: purchaseTons / WORKING_DAYS,
      salesPerDay: salesTons / WORKING_DAYS,
      purchaseTonsMbs: amt(b.purchase?.tons, "mbs"),
      purchaseTonsMcorp: amt(b.purchase?.tons, "mcorp"),
      salesTonsMbs: amt(b.sales?.tons, "mbs"),
      salesTonsMcorp: amt(b.sales?.tons, "mcorp"),
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

export function marketingRepRows(meeting, company) {
  return (meeting?.marketing_reps || []).map((m) => {
    const bs = m.branch_sales || [];
    const branchSales = bs.map((s) => ({
      name: s.name,
      mbs: s.tons?.mbs || 0,
      mcorp: s.tons?.mcorp || 0,
      total: (s.tons?.mbs || 0) + (s.tons?.mcorp || 0),
      value: amt(s.tons, company),
    }));
    // achieve% of tons uses ALL sales by the person (both companies + all branches)
    const totalSalesTons = bs.reduce((acc, s) => acc + (s.tons?.mbs || 0) + (s.tons?.mcorp || 0), 0);
    // sales filtered by the company toggle (for the per-company view total)
    const salesTonsView = branchSales.reduce((acc, b) => acc + b.value, 0);
    const totalVisit = (m.visit?.mbs || 0) + (m.visit?.mcorp || 0);
    const targetTons = m.target_tons || 0;
    const targetParty = m.target_party || 0;
    return {
      name: m.name,
      visit: amt(m.visit, company),
      inquiry: amt(m.inquiry, company),
      inquiryConform: amt(m.inquiry_conform, company),
      orderLoss: amt(m.order_loss, company),
      branchSales,
      salesTonsView,
      totalSalesTons,
      totalVisit,
      targetTons,
      targetParty,
      achieveTonsPct: targetTons ? (totalSalesTons / targetTons) * 100 : 0,
      achievePartyPct: targetParty ? (totalVisit / targetParty) * 100 : 0,
    };
  });
}

export function buildInsights(meeting, company) {
  const k = meetingKpis(meeting, company);
  const reps = repRows(meeting, company);
  const q = quotationRows(meeting, company);
  const insights = [];
  if (!reps.length) return insights;

  if (k.d90Share > 0.2) {
    insights.push({
      type: "danger",
      title: "High 90+ day exposure",
      detail: `${(k.d90Share * 100).toFixed(0)}% of all outstanding (${formatINR(k.d90)}) is stuck in the 90-day bucket — prioritise recovery.`,
    });
  }

  const worst90 = [...reps].sort((a, b) => b.d90 - a.d90)[0];
  if (worst90 && worst90.d90 > 0) {
    insights.push({
      type: "info",
      title: `${worst90.name} holds the largest 90-day overdue`,
      detail: `${formatINR(worst90.d90)} ageing beyond 90 days — needs a dedicated follow-up plan.`,
    });
  }

  const best = [...reps].sort((a, b) => b.collPct - a.collPct)[0];
  if (best && best.collPct > 0) {
    insights.push({
      type: "success",
      title: `${best.name} leads on collection efficiency`,
      detail: `Collected ${formatINR(best.collected)} this week (${best.collPct.toFixed(1)}% of ${formatINR(best.newTarget)} new target).`,
    });
  }

  const worst = [...reps].filter((r) => r.outstanding > 0).sort((a, b) => a.collPct - b.collPct)[0];
  if (worst && worst.name !== best?.name) {
    insights.push({
      type: "warning",
      title: `${worst.name} has the lowest collection rate`,
      detail: `Only ${worst.collPct.toFixed(1)}% collected against ${formatINR(worst.newTarget)} new target this week.`,
    });
  }

  const grew = reps.filter((r) => r.lastTarget > 0 && r.wowDelta > 0).sort((a, b) => b.wowDelta - a.wowDelta)[0];
  if (grew) {
    insights.push({
      type: "warning",
      title: `${grew.name}'s new target grew week-over-week`,
      detail: `Up ${formatINR(grew.wowDelta)} vs last week — collections aren't keeping pace with new dues.`,
    });
  }

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

// ---------- empty factories for forms ----------
const z = () => ({ mbs: 0, mcorp: 0 });

export function emptyRep(name = "") {
  return {
    name,
    aging: { d90: z(), d60: z(), d30: z(), d15: z(), othera: z() },
    weekly_collection: z(), last_week_target: 0, working_days: 6,
  };
}

export function emptyBranch(name = "") {
  return { name, purchase: { tons: z() }, sales: { tons: z() } };
}

export function emptyMarketingRep(name = "") {
  return {
    name, visit: z(), inquiry: z(), inquiry_conform: z(), order_loss: z(),
    branch_sales: [], target_tons: 0, target_party: 0,
  };
}

export function emptyQuotation() {
  return { prepair: z(), conform: z(), pending: z(), under_process: z(), not_conform: z() };
}
