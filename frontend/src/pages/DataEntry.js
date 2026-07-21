import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router-dom";
import { format } from "date-fns";
import { getMeeting, getMeetings, createMeeting, updateMeeting, extractFile, getExtractStatus, formatApiError } from "@/lib/api";
import { emptyRep, emptyBranch, emptyMarketingRep, emptyQuotation, formatINR, formatTons, meetingKpis, WORKING_DAYS } from "@/lib/calc";
import { useAuth } from "@/context/AuthContext";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Calendar } from "@/components/ui/calendar";
import { Loader2, Plus, Trash2, UploadCloud, Save, Calendar as CalendarIcon, Sparkles, FileText, Boxes, Megaphone, Users2, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { toast } from "sonner";

const AGING = [["d90", "90 Days", "#DC2626"], ["d60", "60 Days", "#F59E0B"], ["d30", "30 Days", "#2563EB"], ["othera", "Other", "#6B7280"]];
const QSTAGES = [["prepair", "Prepared"], ["conform", "Confirmed"], ["pending", "Pending"], ["under_process", "Under Process"], ["not_conform", "Not Confirmed"]];
const MKT = [["visit", "Visits"], ["inquiry", "Inquiries"], ["inquiry_conform", "Inq. Confirmed"], ["order_loss", "Order Loss"]];

function DatePicker({ value, onChange, testid }) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="outline" className="w-full justify-start font-normal bg-white" data-testid={testid}>
          <CalendarIcon className="h-4 w-4 mr-2 opacity-60" />
          {value ? format(new Date(value), "dd MMM yyyy") : <span className="text-muted-foreground">Pick a date</span>}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        <Calendar mode="single" selected={value ? new Date(value) : undefined} onSelect={(d) => d && onChange(format(d, "yyyy-MM-dd"))} initialFocus />
      </PopoverContent>
    </Popover>
  );
}

function NumInput({ value, onChange, testid, prefix }) {
  return (
    <div className="relative">
      {prefix && <span className="absolute left-2 top-1/2 -translate-y-1/2 text-[11px] text-muted-foreground">{prefix}</span>}
      <Input type="number" className={`h-9 font-mono text-sm ${prefix ? "pl-5" : ""}`} value={value ? value : ""}
             onChange={(e) => onChange(e.target.value === "" ? 0 : parseFloat(e.target.value))} data-testid={testid} placeholder="0" />
    </div>
  );
}

// two-company amount pair
function AmountPair({ value, onChange, prefix, testidBase }) {
  return (
    <div className="grid grid-cols-2 gap-2">
      <NumInput value={value?.mbs} onChange={(v) => onChange("mbs", v)} prefix={prefix} testid={`${testidBase}-mbs`} />
      <NumInput value={value?.mcorp} onChange={(v) => onChange("mcorp", v)} prefix={prefix} testid={`${testidBase}-mcorp`} />
    </div>
  );
}

function normalizeRep(r) {
  const b = emptyRep(r?.name || "");
  if (!r) return b;
  const m = (x) => ({ mbs: Number(x?.mbs) || 0, mcorp: Number(x?.mcorp) || 0 });
  return {
    name: r.name || "",
    aging: { d90: m(r.aging?.d90), d60: m(r.aging?.d60), d30: m(r.aging?.d30), d15: m(r.aging?.d15), othera: m(r.aging?.othera) },
    weekly_collection: m(r.weekly_collection),
    last_week_target: Number(r.last_week_target) || 0,
    working_days: Number(r.working_days) || 6,
  };
}
function normalizeBranch(b) {
  const base = emptyBranch(b?.name || "");
  if (!b) return base;
  const m = (x) => ({ mbs: Number(x?.mbs) || 0, mcorp: Number(x?.mcorp) || 0 });
  return {
    name: b.name || "",
    purchase: { tons: m(b.purchase?.tons), value: m(b.purchase?.value) },
    sales: { tons: m(b.sales?.tons), value: m(b.sales?.value) },
    sales_return: { amount: m(b.sales_return?.amount), count: m(b.sales_return?.count) },
  };
}
function normalizeMkt(m) {
  const base = emptyMarketingRep(m?.name || "");
  if (!m) return base;
  const a = (x) => ({ mbs: Number(x?.mbs) || 0, mcorp: Number(x?.mcorp) || 0 });
  return {
    name: m.name || "",
    visit: a(m.visit), inquiry: a(m.inquiry), inquiry_conform: a(m.inquiry_conform), order_loss: a(m.order_loss),
    branch_sales: (m.branch_sales || []).map((b) => ({ name: b.name || "", tons: a(b.tons), value: a(b.value) })),
    target_tons: Number(m.target_tons) || 0,
    target_party: Number(m.target_party) || 0,
  };
}
function normalizeQuotation(q) {
  const base = emptyQuotation();
  if (!q) return base;
  const out = {};
  QSTAGES.forEach(([k]) => { out[k] = { mbs: Number(q[k]?.mbs) || 0, mcorp: Number(q[k]?.mcorp) || 0 }; });
  return out;
}

const blankForm = () => ({
  title: "Weekly Collection Meeting", meeting_date: "", period_start: "", period_end: "", notes: "",
  reps: [emptyRep("")], branches: [emptyBranch("Direct Sale")], quotation: emptyQuotation(), marketing_reps: [emptyMarketingRep("")],
});

// "Direct Sale" must always be available as a branch row.
const isDirectSale = (name) => (name || "").trim().toLowerCase().replace(/\s+/g, "") === "directsale";
const withDirectSale = (branches) => {
  const list = branches || [];
  return list.some((b) => isDirectSale(b.name)) ? list : [...list, emptyBranch("Direct Sale")];
};

// ---- Week-over-week helpers ----
// Find the meeting to use as "last week" reference.
//   • If a meeting_date has been picked -> the most recent PRIOR meeting.
//   • If no date yet (fresh form)       -> the most recent EXISTING meeting overall.
//   • Always excludes the meeting currently being edited (editId).
// This mirrors what the user thinks of as "last week" — the immediately
// preceding meeting in chronological order, not "any meeting before today".
function findPreviousMeeting(meetings, currentDate, currentId) {
  if (!meetings || !meetings.length) return null;
  const withDate = meetings.filter((m) => m.id !== currentId && m.meeting_date);
  if (!withDate.length) return null;
  const sortedDesc = [...withDate].sort((a, b) => (a.meeting_date < b.meeting_date ? 1 : -1));
  if (!currentDate) return sortedDesc[0] || null;
  return sortedDesc.find((m) => m.meeting_date < currentDate) || null;
}

// Given a previous meeting doc and a rep name (case-insensitive match),
// return that rep's per-bucket totals from last week plus their New Target.
function prevRepInfo(previousMeeting, name) {
  if (!previousMeeting || !name) return null;
  const key = (name || "").trim().toLowerCase();
  if (!key) return null;
  const r = (previousMeeting.reps || []).find((x) => (x.name || "").trim().toLowerCase() === key);
  if (!r) return null;
  const b = (k) => (Number(r.aging?.[k]?.mbs) || 0) + (Number(r.aging?.[k]?.mcorp) || 0);
  const d90 = b("d90"), d60 = b("d60"), d30 = b("d30"), d15 = b("d15"), othera = b("othera");
  return {
    d90, d60, d30, d15, othera,
    newTarget: d90 + d60 + d30 + d15,
    weekLabel: previousMeeting.week_label || previousMeeting.meeting_date || "",
  };
}

// Small "vs last week" chip: shows previous-week total + delta arrow.
// A lower outstanding is treated as GOOD (green ▼); a rise is a warning (red ▲).
function WowChip({ prev, curr, testid }) {
  if (prev === undefined || prev === null) return null;
  const diff = (Number(curr) || 0) - (Number(prev) || 0);
  const pct = prev > 0 ? (diff / prev) * 100 : (curr > 0 ? 100 : 0);
  const flat = Math.abs(diff) < 1;
  const up = diff > 0;
  const tone = flat ? "text-muted-foreground" : up ? "text-[#DC2626]" : "text-[#16A34A]";
  const Icon = flat ? Minus : up ? TrendingUp : TrendingDown;
  const sign = flat ? "" : up ? "+" : "−";
  return (
    <div className="mt-1 text-[10px] text-muted-foreground flex items-center justify-center gap-1 leading-tight" data-testid={testid}>
      <span>vs&nbsp;<span className="font-mono">{formatINR(prev)}</span></span>
      <span className={`inline-flex items-center gap-0.5 ${tone} font-medium`}>
        <Icon className="h-3 w-3" />
        {flat ? "flat" : `${sign}${Math.abs(pct).toFixed(0)}%`}
      </span>
    </div>
  );
}

export default function DataEntry() {
  const [params] = useSearchParams();
  const editId = params.get("id");
  const navigate = useNavigate();
  const qc = useQueryClient();
  const fileRef = useRef(null);
  const { settings, companyA, companyB } = useAuth();
  const rosterApplied = useRef(false);
  const [form, setForm] = useState(blankForm());
  const [uploading, setUploading] = useState(false);

  const { data: existing, isLoading } = useQuery({ queryKey: ["meeting", editId], queryFn: () => getMeeting(editId), enabled: !!editId });

  // All meetings — used to look up the previous week's data for each rep so
  // we can (a) show a "vs last week" comparison next to each aging bucket and
  // (b) auto-fill each rep's Last Week Target from the previous meeting's
  // New Target instead of asking the user to type it every week.
  const { data: allMeetings } = useQuery({ queryKey: ["meetings"], queryFn: getMeetings });

  const previousMeeting = useMemo(
    () => findPreviousMeeting(allMeetings, form.meeting_date, editId),
    [allMeetings, form.meeting_date, editId],
  );

  // Auto-fill Last Week Target from the previous meeting's per-rep New Target.
  // Rules:
  //   • Only on create (never overwrite persisted values in edit mode).
  //   • Re-fill ALL reps whenever the reference "previous meeting" changes
  //     (e.g. user picks a different meeting_date — so the comparison is
  //     always against the correct prior week).
  //   • Fill freshly-added reps (whose LWT is still 0) even if the reference
  //     hasn't changed.
  //   • Preserve any manual edit as long as the user hasn't changed the date.
  const lastFillSource = useRef(null);
  useEffect(() => {
    if (editId) return;
    if (!previousMeeting) return;
    if (!form.reps || !form.reps.length) return;
    const srcId = previousMeeting.id;
    const sourceChanged = lastFillSource.current !== srcId;
    setForm((prevForm) => {
      const next = structuredClone(prevForm);
      next.reps = next.reps.map((r) => {
        const info = prevRepInfo(previousMeeting, r.name);
        if (!info || info.newTarget <= 0) return r;
        if (sourceChanged || (Number(r.last_week_target) || 0) === 0) {
          return { ...r, last_week_target: Math.round(info.newTarget) };
        }
        return r;
      });
      return next;
    });
    lastFillSource.current = srcId;
  }, [previousMeeting, form.reps.length, editId]);

  // For a NEW meeting, pre-fill a row for each name on the roster (once).
  useEffect(() => {
    if (editId || rosterApplied.current || !settings) return;
    const cr = settings.collection_reps || [];
    const br = settings.branches || [];
    const mr = settings.marketing_reps || [];
    if (!cr.length && !br.length && !mr.length) return; // empty roster -> leave blank form
    rosterApplied.current = true;
    setForm((prev) => ({
      ...prev,
      reps: cr.length ? cr.map((n) => emptyRep(n)) : prev.reps,
      branches: br.length ? withDirectSale(br.map((n) => emptyBranch(n))) : prev.branches,
      marketing_reps: mr.length ? mr.map((n) => emptyMarketingRep(n)) : prev.marketing_reps,
    }));
  }, [settings, editId]);

  const loadRoster = () => {
    const cr = settings?.collection_reps || [];
    const br = settings?.branches || [];
    const mr = settings?.marketing_reps || [];
    if (!cr.length && !br.length && !mr.length) { toast.error("Your roster is empty — add names on the Roster page first"); return; }
    update((f) => {
      if (cr.length) f.reps = cr.map((n) => emptyRep(n));
      if (br.length) f.branches = withDirectSale(br.map((n) => emptyBranch(n)));
      if (mr.length) f.marketing_reps = mr.map((n) => emptyMarketingRep(n));
    });
    toast.success("Rows loaded from roster");
  };

  useEffect(() => {
    if (existing) {
      setForm({
        title: existing.title || "Weekly Collection Meeting",
        meeting_date: existing.meeting_date || "", period_start: existing.period_start || "", period_end: existing.period_end || "",
        notes: existing.notes || "",
        reps: (existing.reps?.length ? existing.reps : [emptyRep("")]).map(normalizeRep),
        branches: withDirectSale((existing.branches?.length ? existing.branches : [emptyBranch("")]).map(normalizeBranch)),
        quotation: normalizeQuotation(existing.quotation),
        marketing_reps: (existing.marketing_reps?.length ? existing.marketing_reps : [emptyMarketingRep("")]).map(normalizeMkt),
      });
    }
  }, [existing]);

  const update = (mutator) => setForm((prev) => { const next = structuredClone(prev); mutator(next); return next; });

  // marketing branch-sales helpers (sales tons + rupee value per branch, per company)
  const getMktBranchSale = (m, branchName, measure = "tons") =>
    (m.branch_sales || []).find((x) => x.name === branchName)?.[measure] || { mbs: 0, mcorp: 0 };
  const setMktBranchSale = (i, branchName, measure, fld, v) => update((f) => {
    const m = f.marketing_reps[i];
    if (!m.branch_sales) m.branch_sales = [];
    let bs = m.branch_sales.find((x) => x.name === branchName);
    if (!bs) { bs = { name: branchName, tons: { mbs: 0, mcorp: 0 }, value: { mbs: 0, mcorp: 0 } }; m.branch_sales.push(bs); }
    if (!bs[measure]) bs[measure] = { mbs: 0, mcorp: 0 };
    bs[measure][fld] = v;
  });

  const save = useMutation({
    mutationFn: (payload) => (editId ? updateMeeting(editId, payload) : createMeeting(payload)),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["meetings"] });
      qc.invalidateQueries({ queryKey: ["meeting", editId] });
      toast.success(editId ? "Meeting updated" : "Meeting created");
      navigate(`/?meeting=${res.id}`);
    },
    onError: (e) => {
      const msg = formatApiError(e.response?.data?.detail) || e.message || "Failed to save";
      toast.error(msg, { duration: 8000 });
      console.error("Save failed:", e.response?.status, e.response?.data || e.message);
    },
  });

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    const fd = new FormData();
    fd.append("file", file);
    toast.info("Reading your file with AI — this can take up to a minute.");
    try {
      const start = await extractFile(fd);
      let data = null;
      for (let i = 0; i < 60; i++) {
        await new Promise((r) => setTimeout(r, 3000));
        const job = await getExtractStatus(start.job_id);
        if (job.status === "done") { data = job.data || {}; break; }
        if (job.status === "error") throw new Error(job.error || "Extraction failed");
      }
      if (!data) throw new Error("Extraction timed out. Please try a smaller file or enter manually.");
      setForm((prev) => ({
        ...prev,
        meeting_date: data.meeting_date || prev.meeting_date,
        period_start: data.period_start || prev.period_start,
        period_end: data.period_end || prev.period_end,
        reps: (data.reps?.length ? data.reps : prev.reps).map(normalizeRep),
        branches: (data.branches?.length ? data.branches : prev.branches).map(normalizeBranch),
        quotation: normalizeQuotation(data.quotation),
        marketing_reps: (data.marketing_reps?.length ? data.marketing_reps : prev.marketing_reps).map(normalizeMkt),
      }));
      toast.success(`Extracted ${data.reps?.length || 0} reps, ${data.branches?.length || 0} branches — review & save`);
    } catch (err) {
      toast.error(err.message || "Extraction failed");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const submit = () => {
    if (!form.meeting_date) {
      toast.error("Please select a meeting date", { duration: 6000 });
      return;
    }
    // Silently drop rows the user "added" but never named — matches how
    // branches / marketing_reps have always been treated. This prevents the
    // classic "clicked Add Rep, forgot to name it, save does nothing" trap.
    const cleanReps = form.reps.filter((r) => (r.name || "").trim());
    if (cleanReps.length === 0) {
      toast.error("Please add at least one collection rep with a name", { duration: 6000 });
      return;
    }
    const branchNames = form.branches.map((b) => (b.name || "").trim()).filter(Boolean);
    const payload = {
      ...form,
      reps: cleanReps,
      branches: form.branches.filter((b) => (b.name || "").trim()),
      marketing_reps: form.marketing_reps.filter((m) => (m.name || "").trim()).map((m) => ({
        ...m,
        // keep only branch sales that match a current branch name
        branch_sales: (m.branch_sales || []).filter((bs) => branchNames.includes((bs.name || "").trim())),
      })),
    };
    save.mutate(payload);
  };

  if (editId && isLoading) return <div className="flex items-center justify-center py-32"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>;

  const preview = meetingKpis(form, "all");
  const branchOptions = form.branches.map((b) => (b.name || "").trim()).filter(Boolean);

  return (
    <div className="space-y-6 pb-12" data-testid="data-entry-page">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground mb-1">{editId ? "Edit" : "New Entry"}</div>
          <h1 className="text-3xl font-semibold tracking-tighter">{editId ? "Edit Meeting" : "Add Weekly Meeting"}</h1>
          <p className="text-sm text-muted-foreground mt-1">Upload the meeting PDF/Excel to auto-fill, or enter everything manually.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => navigate("/meetings")}>Cancel</Button>
          <Button onClick={submit} disabled={save.isPending} data-testid="save-meeting-button">
            {save.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} Save Meeting
          </Button>
        </div>
      </div>

      {/* Upload */}
      <Card className="p-6 shadow-none border-dashed border-2" data-testid="upload-card">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="h-11 w-11 rounded-md bg-black flex items-center justify-center"><Sparkles className="h-5 w-5 text-white" /></div>
            <div>
              <h3 className="text-base font-medium">AI Auto-Extract</h3>
              <p className="text-sm text-muted-foreground">Upload a meeting PDF, Excel or CSV — we read the collection, branch &amp; marketing tables and fill the form below.</p>
            </div>
          </div>
          <input ref={fileRef} type="file" accept=".pdf,.xlsx,.xls,.csv" hidden onChange={handleUpload} data-testid="file-input" />
          <Button variant="secondary" onClick={() => fileRef.current?.click()} disabled={uploading} data-testid="upload-extract-button">
            {uploading ? <><Loader2 className="h-4 w-4 animate-spin" /> Extracting…</> : <><UploadCloud className="h-4 w-4" /> Upload File</>}
          </Button>
        </div>
      </Card>

      {/* Meta */}
      <Card className="p-6 shadow-none">
        <h3 className="text-base font-medium mb-4 flex items-center gap-2"><FileText className="h-4 w-4" /> Meeting Details</h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="space-y-2"><Label className="text-xs uppercase tracking-wider text-muted-foreground">Meeting Date</Label>
            <DatePicker value={form.meeting_date} onChange={(v) => update((f) => (f.meeting_date = v))} testid="meeting-date-picker" /></div>
          <div className="space-y-2"><Label className="text-xs uppercase tracking-wider text-muted-foreground">Period Start</Label>
            <DatePicker value={form.period_start} onChange={(v) => update((f) => (f.period_start = v))} testid="period-start-picker" /></div>
          <div className="space-y-2"><Label className="text-xs uppercase tracking-wider text-muted-foreground">Period End</Label>
            <DatePicker value={form.period_end} onChange={(v) => update((f) => (f.period_end = v))} testid="period-end-picker" /></div>
          <div className="space-y-2"><Label className="text-xs uppercase tracking-wider text-muted-foreground">Title</Label>
            <Input value={form.title} onChange={(e) => update((f) => (f.title = e.target.value))} data-testid="meeting-title-input" /></div>
        </div>
      </Card>

      {/* Roster hint when empty */}
      {!editId && settings && !(settings.collection_reps?.length || settings.branches?.length || settings.marketing_reps?.length) && (
        <Card className="p-4 shadow-none border-dashed bg-secondary/30" data-testid="roster-hint">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <p className="text-sm text-muted-foreground">
              Add your representatives and branches once on the <span className="font-medium text-foreground">Roster</span> page, and they will auto-fill here every week — you will only enter numbers.
            </p>
            <Button variant="outline" size="sm" onClick={() => navigate("/settings")} data-testid="goto-roster">Go to Roster</Button>
          </div>
        </Card>
      )}

      {/* Collection Reps */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-medium flex items-center gap-2"><Users2 className="h-5 w-5" /> Collection Reps ({form.reps.length})</h3>
          <div className="flex items-center gap-2">
            {!editId && <Button variant="outline" size="sm" onClick={loadRoster} data-testid="load-roster-button"><Users2 className="h-4 w-4" /> Load from roster</Button>}
            <Button variant="secondary" size="sm" onClick={() => update((f) => f.reps.push(emptyRep("")))} data-testid="add-rep-button"><Plus className="h-4 w-4" /> Add Rep</Button>
          </div>
        </div>
        {form.reps.map((rep, i) => {
          const prev = prevRepInfo(previousMeeting, rep.name);
          return (
          <Card key={i} className="p-6 shadow-none" data-testid={`rep-card-${i}`}>
            <div className="flex items-center justify-between mb-4">
              <Input value={rep.name} placeholder="Representative name" className="max-w-xs font-medium"
                     onChange={(e) => update((f) => (f.reps[i].name = e.target.value))} data-testid={`rep-name-${i}`} />
              <div className="flex items-center gap-3">
                {prev && (
                  <span className="text-[10px] uppercase tracking-wider text-muted-foreground hidden sm:inline" data-testid={`rep-${i}-prev-week`}>
                    vs {prev.weekLabel}
                  </span>
                )}
                <Button variant="ghost" size="icon" className="text-[#DC2626]" onClick={() => update((f) => f.reps.splice(i, 1))} disabled={form.reps.length === 1} data-testid={`remove-rep-${i}`}><Trash2 className="h-4 w-4" /></Button>
              </div>
            </div>
            <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mb-3">Outstanding — {companyA} / {companyB} per bucket</div>
            <div className="space-y-2">
              <div className="grid grid-cols-12 gap-3 items-center text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                <span className="col-span-2" />
                <span className="col-span-3 text-center">{companyA}</span>
                <span className="col-span-3 text-center">{companyB}</span>
                <span className="col-span-4 text-center">Total ({companyA}+{companyB})</span>
              </div>
              {AGING.map(([key, label, color]) => {
                const tot = (rep.aging[key]?.mbs || 0) + (rep.aging[key]?.mcorp || 0);
                return (
                  <div key={key} className="grid grid-cols-12 gap-3 items-center rounded-md border border-border/60 bg-secondary/20 px-3 py-2">
                    <span className="col-span-2 flex items-center gap-2 text-sm"><span className="h-2.5 w-2.5 rounded-sm shrink-0" style={{ background: color }} />{label}</span>
                    <div className="col-span-3"><NumInput value={rep.aging[key]?.mbs} prefix="₹" testid={`rep-${i}-${key}-mbs`} onChange={(v) => update((f) => (f.reps[i].aging[key].mbs = v))} /></div>
                    <div className="col-span-3"><NumInput value={rep.aging[key]?.mcorp} prefix="₹" testid={`rep-${i}-${key}-mcorp`} onChange={(v) => update((f) => (f.reps[i].aging[key].mcorp = v))} /></div>
                    <div className="col-span-4 text-center">
                      <div className="font-mono tabular-nums text-sm font-semibold" style={{ color }} data-testid={`rep-${i}-${key}-total`}>{formatINR(tot)}</div>
                      {prev && <WowChip prev={prev[key]} curr={tot} testid={`rep-${i}-${key}-wow`} />}
                    </div>
                  </div>
                );
              })}
              {(() => {
                const tot = rep.aging.d15?.mcorp || 0;
                return (
                  <div className="grid grid-cols-12 gap-3 items-center rounded-md border border-border/60 bg-secondary/20 px-3 py-2">
                    <span className="col-span-2 flex items-center gap-2 text-sm"><span className="h-2.5 w-2.5 rounded-sm shrink-0" style={{ background: "#0EA5E9" }} />15 Days</span>
                    <div className="col-span-3 h-9 rounded-md border border-dashed border-border flex items-center justify-center text-xs text-muted-foreground select-none">{companyA} n/a</div>
                    <div className="col-span-3"><NumInput value={rep.aging.d15?.mcorp} prefix="₹" testid={`rep-${i}-d15-mcorp`} onChange={(v) => update((f) => (f.reps[i].aging.d15.mcorp = v))} /></div>
                    <div className="col-span-4 text-center">
                      <div className="font-mono tabular-nums text-sm font-semibold text-[#0EA5E9]" data-testid={`rep-${i}-d15-total`}>{formatINR(tot)}</div>
                      {prev && <WowChip prev={prev.d15} curr={tot} testid={`rep-${i}-d15-wow`} />}
                    </div>
                  </div>
                );
              })()}
              {(() => {
                const keys = ["d90", "d60", "d30", "d15", "othera"];
                const sumMbs = keys.reduce((s, k) => s + (rep.aging[k]?.mbs || 0), 0);
                const sumMcorp = keys.reduce((s, k) => s + (rep.aging[k]?.mcorp || 0), 0);
                const sumTot = sumMbs + sumMcorp;
                const prevSum = prev ? (prev.d90 + prev.d60 + prev.d30 + prev.d15 + prev.othera) : null;
                return (
                  <div className="grid grid-cols-12 gap-3 items-center rounded-md border-2 border-foreground/80 bg-foreground text-background px-3 py-2.5" data-testid={`rep-${i}-aging-sum-row`}>
                    <span className="col-span-2 text-[11px] font-semibold uppercase tracking-wider">All Buckets</span>
                    <div className="col-span-3 text-center font-mono tabular-nums text-sm font-semibold" data-testid={`rep-${i}-aging-sum-mbs`}>{formatINR(sumMbs)}</div>
                    <div className="col-span-3 text-center font-mono tabular-nums text-sm font-semibold" data-testid={`rep-${i}-aging-sum-mcorp`}>{formatINR(sumMcorp)}</div>
                    <div className="col-span-4 text-center">
                      <div className="font-mono tabular-nums text-base font-bold" data-testid={`rep-${i}-aging-sum-total`}>{formatINR(sumTot)}</div>
                      {prev && prevSum !== null && (
                        <div className="text-[10px] mt-0.5 flex items-center justify-center gap-1 text-background/70" data-testid={`rep-${i}-aging-sum-wow`}>
                          <span>vs <span className="font-mono">{formatINR(prevSum)}</span></span>
                          {(() => {
                            const diff = sumTot - prevSum;
                            const pct = prevSum > 0 ? (diff / prevSum) * 100 : 0;
                            if (Math.abs(diff) < 1) return <span className="opacity-70">flat</span>;
                            const up = diff > 0;
                            return <span className={up ? "text-[#FCA5A5]" : "text-[#86EFAC]"}>{up ? "▲" : "▼"} {Math.abs(pct).toFixed(0)}%</span>;
                          })()}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })()}
            </div>
            <Separator className="my-4" />
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 items-end">
              <div className="space-y-1.5 col-span-2"><Label className="text-xs text-muted-foreground">Collection This Week ({companyA} / {companyB})</Label>
                <AmountPair value={rep.weekly_collection} prefix="₹" testidBase={`rep-${i}-weekly-collection`} onChange={(fld, v) => update((f) => (f.reps[i].weekly_collection[fld] = v))} />
                <div className="text-[11px] text-muted-foreground">Total: <span className="font-mono text-foreground">{formatINR((rep.weekly_collection?.mbs || 0) + (rep.weekly_collection?.mcorp || 0))}</span></div>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">Last Week Target (₹)</Label>
                <NumInput value={rep.last_week_target} prefix="₹" testid={`rep-${i}-last-week-target`} onChange={(v) => update((f) => (f.reps[i].last_week_target = v))} />
                {prev && prev.newTarget > 0 && (
                  <div className="text-[10px] text-muted-foreground leading-tight" data-testid={`rep-${i}-lwt-hint`}>
                    {editId
                      ? <>Last week&rsquo;s New Target was <span className="font-mono">{formatINR(prev.newTarget)}</span>.</>
                      : <>Auto-filled from last week&rsquo;s New Target (<span className="font-mono">{formatINR(prev.newTarget)}</span>). Edit if needed.</>}
                  </div>
                )}
              </div>
              <div className="space-y-1.5"><Label className="text-xs text-muted-foreground">Working Days</Label>
                <NumInput value={rep.working_days} testid={`rep-${i}-working-days`} onChange={(v) => update((f) => (f.reps[i].working_days = v || 6))} /></div>
              {(() => {
                const newTarget = ["d90", "d60", "d30", "d15"].reduce((s, b) => s + (rep.aging[b]?.mbs || 0) + (rep.aging[b]?.mcorp || 0), 0);
                const coll = (rep.weekly_collection?.mbs || 0) + (rep.weekly_collection?.mcorp || 0);
                const wd = rep.working_days || 6;
                const lwt = rep.last_week_target || 0;
                return (
                  <>
                    <div className="rounded-md border border-border px-3 py-2 bg-secondary/40">
                      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">New Target (90+60+30+15)</div>
                      <div className="font-mono text-sm" data-testid={`rep-${i}-new-target`}>{formatINR(newTarget)}</div>
                    </div>
                    <div className="rounded-md border border-border px-3 py-2 bg-secondary/40">
                      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Coll / Day</div>
                      <div className="font-mono text-sm" data-testid={`rep-${i}-coll-day`}>{formatINR(coll / wd)}</div>
                    </div>
                    <div className="rounded-md border border-border px-3 py-2 bg-secondary/40">
                      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Coll % (÷ Last Week Target)</div>
                      <div className="font-mono text-sm" data-testid={`rep-${i}-coll-pct`}>{lwt ? ((coll / lwt) * 100).toFixed(1) : "0.0"}%</div>
                    </div>
                  </>
                );
              })()}
            </div>
          </Card>
          );
        })}
      </div>

      {/* Branches */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-medium flex items-center gap-2"><Boxes className="h-5 w-5" /> Branch Sales &amp; Purchase ({form.branches.length})</h3>
          <Button variant="secondary" size="sm" onClick={() => update((f) => f.branches.push(emptyBranch("")))} data-testid="add-branch-button"><Plus className="h-4 w-4" /> Add Branch</Button>
        </div>
        {form.branches.map((b, i) => (
          <Card key={i} className="p-6 shadow-none" data-testid={`branch-card-${i}`}>
            <div className="flex items-center justify-between mb-4">
              <Input value={b.name} placeholder="Branch name" className="max-w-xs font-medium"
                     onChange={(e) => update((f) => (f.branches[i].name = e.target.value))} data-testid={`branch-name-${i}`} />
              <Button variant="ghost" size="icon" className="text-[#DC2626]" onClick={() => update((f) => f.branches.splice(i, 1))} data-testid={`remove-branch-${i}`}><Trash2 className="h-4 w-4" /></Button>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-x-8 gap-y-4">
              <div className="space-y-3">
                <div className="text-[11px] font-semibold uppercase tracking-wider text-[#2563EB]">Purchase ({companyA} / {companyB})</div>
                <div className="flex items-center gap-3"><span className="text-xs w-12 text-muted-foreground">Tons</span><div className="flex-1"><AmountPair value={b.purchase.tons} testidBase={`branch-${i}-purchase-tons`} onChange={(fld, v) => update((f) => (f.branches[i].purchase.tons[fld] = v))} /></div></div>
                <div className="flex items-center gap-3"><span className="text-xs w-12 text-muted-foreground">Value</span><div className="flex-1"><AmountPair value={b.purchase.value} prefix="₹" testidBase={`branch-${i}-purchase-value`} onChange={(fld, v) => update((f) => (f.branches[i].purchase.value[fld] = v))} /></div></div>
                {(() => {
                  const t = (b.purchase?.tons?.mbs || 0) + (b.purchase?.tons?.mcorp || 0);
                  const v = (b.purchase?.value?.mbs || 0) + (b.purchase?.value?.mcorp || 0);
                  return (
                    <div className="flex gap-2 pl-[60px]">
                      <div className="flex-1 rounded-md border border-border px-3 py-1.5 bg-secondary/40"><div className="text-[9px] uppercase tracking-wider text-muted-foreground">Total</div><div className="font-mono text-sm text-[#2563EB]" data-testid={`branch-${i}-purchase-total`}>{formatTons(t)}</div></div>
                      <div className="flex-1 rounded-md border border-border px-3 py-1.5 bg-secondary/40"><div className="text-[9px] uppercase tracking-wider text-muted-foreground">Per Day (÷{WORKING_DAYS})</div><div className="font-mono text-sm text-[#2563EB]/80" data-testid={`branch-${i}-purchase-perday`}>{formatTons(t / WORKING_DAYS)}</div></div>
                      <div className="flex-1 rounded-md border border-border px-3 py-1.5 bg-secondary/40"><div className="text-[9px] uppercase tracking-wider text-muted-foreground">Total Value</div><div className="font-mono text-sm text-[#2563EB]" data-testid={`branch-${i}-purchase-value-total`}>{formatINR(v)}</div></div>
                    </div>
                  );
                })()}
              </div>
              <div className="space-y-3">
                <div className="text-[11px] font-semibold uppercase tracking-wider text-[#16A34A]">Sales ({companyA} / {companyB})</div>
                <div className="flex items-center gap-3"><span className="text-xs w-12 text-muted-foreground">Tons</span><div className="flex-1"><AmountPair value={b.sales.tons} testidBase={`branch-${i}-sales-tons`} onChange={(fld, v) => update((f) => (f.branches[i].sales.tons[fld] = v))} /></div></div>
                <div className="flex items-center gap-3"><span className="text-xs w-12 text-muted-foreground">Value</span><div className="flex-1"><AmountPair value={b.sales.value} prefix="₹" testidBase={`branch-${i}-sales-value`} onChange={(fld, v) => update((f) => (f.branches[i].sales.value[fld] = v))} /></div></div>
                {(() => {
                  const t = (b.sales?.tons?.mbs || 0) + (b.sales?.tons?.mcorp || 0);
                  const v = (b.sales?.value?.mbs || 0) + (b.sales?.value?.mcorp || 0);
                  return (
                    <div className="flex gap-2 pl-[60px]">
                      <div className="flex-1 rounded-md border border-border px-3 py-1.5 bg-secondary/40"><div className="text-[9px] uppercase tracking-wider text-muted-foreground">Total</div><div className="font-mono text-sm text-[#16A34A]" data-testid={`branch-${i}-sales-total`}>{formatTons(t)}</div></div>
                      <div className="flex-1 rounded-md border border-border px-3 py-1.5 bg-secondary/40"><div className="text-[9px] uppercase tracking-wider text-muted-foreground">Per Day (÷{WORKING_DAYS})</div><div className="font-mono text-sm text-[#16A34A]/80" data-testid={`branch-${i}-sales-perday`}>{formatTons(t / WORKING_DAYS)}</div></div>
                      <div className="flex-1 rounded-md border border-border px-3 py-1.5 bg-secondary/40"><div className="text-[9px] uppercase tracking-wider text-muted-foreground">Total Value</div><div className="font-mono text-sm text-[#16A34A]" data-testid={`branch-${i}-sales-value-total`}>{formatINR(v)}</div></div>
                    </div>
                  );
                })()}
              </div>
            </div>

            <Separator className="my-4" />
            <div className="space-y-3">
              <div className="text-[11px] font-semibold uppercase tracking-wider text-[#D97706]">Sales Return ({companyA} / {companyB})</div>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-x-8 gap-y-3">
                <div className="flex items-center gap-3"><span className="text-xs w-12 text-muted-foreground">Amount</span><div className="flex-1"><AmountPair value={b.sales_return?.amount} prefix="₹" testidBase={`branch-${i}-return-amount`} onChange={(fld, v) => update((f) => (f.branches[i].sales_return.amount[fld] = v))} /></div></div>
                <div className="flex items-center gap-3"><span className="text-xs w-12 text-muted-foreground">Count</span><div className="flex-1"><AmountPair value={b.sales_return?.count} testidBase={`branch-${i}-return-count`} onChange={(fld, v) => update((f) => (f.branches[i].sales_return.count[fld] = v))} /></div></div>
              </div>
              {(() => {
                const a = (b.sales_return?.amount?.mbs || 0) + (b.sales_return?.amount?.mcorp || 0);
                const c = (b.sales_return?.count?.mbs || 0) + (b.sales_return?.count?.mcorp || 0);
                return (
                  <div className="flex gap-2 pl-[60px] max-w-md">
                    <div className="flex-1 rounded-md border border-border px-3 py-1.5 bg-secondary/40"><div className="text-[9px] uppercase tracking-wider text-muted-foreground">Total Amount</div><div className="font-mono text-sm text-[#D97706]" data-testid={`branch-${i}-return-amount-total`}>{formatINR(a)}</div></div>
                    <div className="flex-1 rounded-md border border-border px-3 py-1.5 bg-secondary/40"><div className="text-[9px] uppercase tracking-wider text-muted-foreground">Total Count</div><div className="font-mono text-sm text-[#D97706]" data-testid={`branch-${i}-return-count-total`}>{c}</div></div>
                  </div>
                );
              })()}
            </div>
          </Card>
        ))}
      </div>

      {/* Quotation */}
      <Card className="p-6 shadow-none" data-testid="quotation-editor">
        <h3 className="text-base font-medium mb-4">Quotation Pipeline (counts)</h3>
        <div className="space-y-2.5 max-w-2xl">
          <div className="grid grid-cols-12 gap-2 text-[10px] uppercase tracking-wider text-muted-foreground">
            <span className="col-span-4">Stage</span><span className="col-span-4">{companyA}</span><span className="col-span-4">{companyB}</span>
          </div>
          {QSTAGES.map(([key, label]) => (
            <div key={key} className="grid grid-cols-12 gap-2 items-center">
              <span className="col-span-4 text-sm">{label}</span>
              <div className="col-span-8"><AmountPair value={form.quotation[key]} testidBase={`quotation-${key}`} onChange={(fld, v) => update((f) => (f.quotation[key][fld] = v))} /></div>
            </div>
          ))}
        </div>
      </Card>

      {/* Marketing reps */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-medium flex items-center gap-2"><Megaphone className="h-5 w-5" /> Marketing Activity ({form.marketing_reps.length})</h3>
          <Button variant="secondary" size="sm" onClick={() => update((f) => f.marketing_reps.push(emptyMarketingRep("")))} data-testid="add-marketing-button"><Plus className="h-4 w-4" /> Add Person</Button>
        </div>
        {form.marketing_reps.map((m, i) => (
          <Card key={i} className="p-6 shadow-none" data-testid={`marketing-card-${i}`}>
            <div className="flex items-center justify-between mb-4">
              <Input value={m.name} placeholder="Marketing person" className="max-w-xs font-medium"
                     onChange={(e) => update((f) => (f.marketing_reps[i].name = e.target.value))} data-testid={`marketing-name-${i}`} />
              <Button variant="ghost" size="icon" className="text-[#DC2626]" onClick={() => update((f) => f.marketing_reps.splice(i, 1))} data-testid={`remove-marketing-${i}`}><Trash2 className="h-4 w-4" /></Button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-3">
              {MKT.map(([key, label]) => (
                <div key={key} className="flex items-center gap-3">
                  <span className="text-sm w-28 shrink-0 text-muted-foreground">{label}</span>
                  <div className="flex-1"><AmountPair value={m[key]} testidBase={`marketing-${i}-${key}`} onChange={(fld, v) => update((f) => (f.marketing_reps[i][key][fld] = v))} /></div>
                </div>
              ))}
            </div>

            <Separator className="my-4" />
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 items-end">
              <div className="space-y-1.5"><Label className="text-xs text-muted-foreground">Target Tons</Label>
                <NumInput value={m.target_tons} testid={`marketing-${i}-target-tons`} onChange={(v) => update((f) => (f.marketing_reps[i].target_tons = v))} /></div>
              <div className="space-y-1.5"><Label className="text-xs text-muted-foreground">Target Party (visits)</Label>
                <NumInput value={m.target_party} testid={`marketing-${i}-target-party`} onChange={(v) => update((f) => (f.marketing_reps[i].target_party = v))} /></div>
              {(() => {
                const totalSales = (m.branch_sales || []).reduce((s, b) => s + (b.tons?.mbs || 0) + (b.tons?.mcorp || 0), 0);
                const totalVisit = (m.visit?.mbs || 0) + (m.visit?.mcorp || 0);
                const at = m.target_tons ? (totalSales / m.target_tons) * 100 : 0;
                const ap = m.target_party ? (totalVisit / m.target_party) * 100 : 0;
                return (
                  <>
                    <div className="rounded-md border border-border px-3 py-2 bg-secondary/40">
                      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Achieve% Tons</div>
                      <div className="font-mono text-sm">{at.toFixed(1)}% <span className="text-[10px] text-muted-foreground">({totalSales.toFixed(1)} T)</span></div>
                    </div>
                    <div className="rounded-md border border-border px-3 py-2 bg-secondary/40">
                      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Achieve% Party</div>
                      <div className="font-mono text-sm">{ap.toFixed(1)}% <span className="text-[10px] text-muted-foreground">({totalVisit} visits)</span></div>
                    </div>
                  </>
                );
              })()}
            </div>

            <div className="mt-4">
              <div className="text-[11px] font-semibold uppercase tracking-wider text-[#16A34A] mb-2">Sales by Branch — Tons &amp; Value ({companyA} / {companyB})</div>
              {branchOptions.length === 0 ? (
                <p className="text-xs text-muted-foreground">Add branches in the &ldquo;Branch Sales &amp; Purchase&rdquo; section above to record branch-wise sales here.</p>
              ) : (
                <div className="space-y-3">
                  <div className="hidden md:grid grid-cols-2 gap-x-8">
                    {[0, 1].map((c) => (
                      <div key={c} className="flex items-center gap-3">
                        <span className="w-28 shrink-0" />
                        <div className="flex-1 grid grid-cols-2 gap-2 text-[10px] uppercase tracking-wider text-muted-foreground text-center">
                          <span>Tons ({companyA} / {companyB})</span><span>Value ₹ ({companyA} / {companyB})</span>
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-3">
                    {branchOptions.map((bn) => (
                      <div key={bn} className="flex items-center gap-3">
                        <span className="text-sm w-28 shrink-0 text-muted-foreground truncate" title={bn}>{bn}</span>
                        <div className="flex-1 grid grid-cols-2 gap-2">
                          <AmountPair value={getMktBranchSale(m, bn, "tons")} testidBase={`marketing-${i}-branchsale-${bn}`} onChange={(fld, v) => setMktBranchSale(i, bn, "tons", fld, v)} />
                          <AmountPair value={getMktBranchSale(m, bn, "value")} prefix="₹" testidBase={`marketing-${i}-branchvalue-${bn}`} onChange={(fld, v) => setMktBranchSale(i, bn, "value", fld, v)} />
                        </div>
                      </div>
                    ))}
                  </div>
                  {(() => {
                    const tv = (m.branch_sales || []).reduce((s, b) => s + (b.value?.mbs || 0) + (b.value?.mcorp || 0), 0);
                    const tt = (m.branch_sales || []).reduce((s, b) => s + (b.tons?.mbs || 0) + (b.tons?.mcorp || 0), 0);
                    return (
                      <div className="flex gap-2 max-w-md">
                        <div className="flex-1 rounded-md border border-border px-3 py-1.5 bg-secondary/40"><div className="text-[9px] uppercase tracking-wider text-muted-foreground">Total Tons</div><div className="font-mono text-sm text-[#16A34A]" data-testid={`marketing-${i}-branchsale-total-tons`}>{formatTons(tt)}</div></div>
                        <div className="flex-1 rounded-md border border-border px-3 py-1.5 bg-secondary/40"><div className="text-[9px] uppercase tracking-wider text-muted-foreground">Total Value</div><div className="font-mono text-sm text-[#16A34A]" data-testid={`marketing-${i}-branchsale-total-value`}>{formatINR(tv)}</div></div>
                      </div>
                    );
                  })()}
                </div>
              )}
            </div>
          </Card>
        ))}
      </div>

      {/* Notes + preview */}
      <Card className="p-6 shadow-none">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="md:col-span-2 space-y-2">
            <Label className="text-xs uppercase tracking-wider text-muted-foreground">Meeting Notes</Label>
            <Textarea rows={3} value={form.notes} onChange={(e) => update((f) => (f.notes = e.target.value))} placeholder="Key discussion points, action items…" data-testid="notes-input" />
          </div>
          <div className="rounded-md border border-border p-4 bg-secondary/40">
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Live Total Outstanding</div>
            <div className="font-mono tabular-nums text-2xl mt-1">{formatINR(preview.totalOutstanding)}</div>
            <Separator className="my-3" />
            <div className="flex justify-between text-sm"><span className="text-muted-foreground">90 Days</span><span className="font-mono text-[#DC2626]">{formatINR(preview.d90)}</span></div>
            <div className="flex justify-between text-sm mt-1"><span className="text-muted-foreground">Collected</span><span className="font-mono text-[#16A34A]">{formatINR(preview.collected)}</span></div>
          </div>
        </div>
      </Card>
    </div>
  );
}
