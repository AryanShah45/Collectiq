import { useEffect, useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router-dom";
import { format } from "date-fns";
import { getMeeting, createMeeting, updateMeeting, extractFile, getExtractStatus, formatApiError } from "@/lib/api";
import { emptyRep, emptyBranch, emptyMarketingRep, emptyQuotation, formatINR, meetingKpis } from "@/lib/calc";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Calendar } from "@/components/ui/calendar";
import { Loader2, Plus, Trash2, UploadCloud, Save, Calendar as CalendarIcon, Sparkles, FileText, Boxes, Megaphone, Users2 } from "lucide-react";
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

// MBS / MCORP pair
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
    aging: { d90: m(r.aging?.d90), d60: m(r.aging?.d60), d30: m(r.aging?.d30), othera: m(r.aging?.othera) },
    weekly_collection: Number(r.weekly_collection) || 0,
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
    purchase: { value: m(b.purchase?.value), tons: m(b.purchase?.tons) },
    sales: { value: m(b.sales?.value), tons: m(b.sales?.tons) },
  };
}
function normalizeMkt(m) {
  const base = emptyMarketingRep(m?.name || "");
  if (!m) return base;
  const a = (x) => ({ mbs: Number(x?.mbs) || 0, mcorp: Number(x?.mcorp) || 0 });
  return { name: m.name || "", visit: a(m.visit), inquiry: a(m.inquiry), inquiry_conform: a(m.inquiry_conform), order_loss: a(m.order_loss) };
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
  reps: [emptyRep("")], branches: [emptyBranch("")], quotation: emptyQuotation(), marketing_reps: [emptyMarketingRep("")],
});

export default function DataEntry() {
  const [params] = useSearchParams();
  const editId = params.get("id");
  const navigate = useNavigate();
  const qc = useQueryClient();
  const fileRef = useRef(null);
  const [form, setForm] = useState(blankForm());
  const [uploading, setUploading] = useState(false);

  const { data: existing, isLoading } = useQuery({ queryKey: ["meeting", editId], queryFn: () => getMeeting(editId), enabled: !!editId });

  useEffect(() => {
    if (existing) {
      setForm({
        title: existing.title || "Weekly Collection Meeting",
        meeting_date: existing.meeting_date || "", period_start: existing.period_start || "", period_end: existing.period_end || "",
        notes: existing.notes || "",
        reps: (existing.reps?.length ? existing.reps : [emptyRep("")]).map(normalizeRep),
        branches: (existing.branches?.length ? existing.branches : [emptyBranch("")]).map(normalizeBranch),
        quotation: normalizeQuotation(existing.quotation),
        marketing_reps: (existing.marketing_reps?.length ? existing.marketing_reps : [emptyMarketingRep("")]).map(normalizeMkt),
      });
    }
  }, [existing]);

  const update = (mutator) => setForm((prev) => { const next = structuredClone(prev); mutator(next); return next; });

  const save = useMutation({
    mutationFn: (payload) => (editId ? updateMeeting(editId, payload) : createMeeting(payload)),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["meetings"] });
      qc.invalidateQueries({ queryKey: ["meeting", editId] });
      toast.success(editId ? "Meeting updated" : "Meeting created");
      navigate(`/?meeting=${res.id}`);
    },
    onError: (e) => toast.error(formatApiError(e.response?.data?.detail) || "Failed to save"),
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
    if (!form.meeting_date) { toast.error("Please select a meeting date"); return; }
    if (form.reps.some((r) => !r.name.trim())) { toast.error("Every collection rep needs a name"); return; }
    const payload = {
      ...form,
      branches: form.branches.filter((b) => b.name.trim()),
      marketing_reps: form.marketing_reps.filter((m) => m.name.trim()),
    };
    save.mutate(payload);
  };

  if (editId && isLoading) return <div className="flex items-center justify-center py-32"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>;

  const preview = meetingKpis(form, "all");

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

      {/* Collection Reps */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-medium flex items-center gap-2"><Users2 className="h-5 w-5" /> Collection Reps ({form.reps.length})</h3>
          <Button variant="secondary" size="sm" onClick={() => update((f) => f.reps.push(emptyRep("")))} data-testid="add-rep-button"><Plus className="h-4 w-4" /> Add Rep</Button>
        </div>
        {form.reps.map((rep, i) => (
          <Card key={i} className="p-6 shadow-none" data-testid={`rep-card-${i}`}>
            <div className="flex items-center justify-between mb-4">
              <Input value={rep.name} placeholder="Representative name" className="max-w-xs font-medium"
                     onChange={(e) => update((f) => (f.reps[i].name = e.target.value))} data-testid={`rep-name-${i}`} />
              <Button variant="ghost" size="icon" className="text-[#DC2626]" onClick={() => update((f) => f.reps.splice(i, 1))} disabled={form.reps.length === 1} data-testid={`remove-rep-${i}`}><Trash2 className="h-4 w-4" /></Button>
            </div>
            <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mb-3">Outstanding — MBS / MCORP per bucket</div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-3">
              {AGING.map(([key, label, color]) => (
                <div key={key} className="flex items-center gap-3">
                  <span className="flex items-center gap-2 text-sm w-24 shrink-0"><span className="h-2.5 w-2.5 rounded-sm" style={{ background: color }} />{label}</span>
                  <div className="flex-1"><AmountPair value={rep.aging[key]} prefix="₹" testidBase={`rep-${i}-${key}`} onChange={(fld, v) => update((f) => (f.reps[i].aging[key][fld] = v))} /></div>
                </div>
              ))}
            </div>
            <Separator className="my-4" />
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 items-end">
              <div className="space-y-1.5"><Label className="text-xs text-muted-foreground">Collection This Week</Label>
                <NumInput value={rep.weekly_collection} prefix="₹" testid={`rep-${i}-weekly-collection`} onChange={(v) => update((f) => (f.reps[i].weekly_collection = v))} /></div>
              <div className="space-y-1.5"><Label className="text-xs text-muted-foreground">Working Days</Label>
                <NumInput value={rep.working_days} testid={`rep-${i}-working-days`} onChange={(v) => update((f) => (f.reps[i].working_days = v || 6))} /></div>
              <div className="rounded-md border border-border px-3 py-2 bg-secondary/40">
                <div className="text-[10px] uppercase tracking-wider text-muted-foreground">New Target (Outstanding)</div>
                <div className="font-mono text-sm">{formatINR(["d90", "d60", "d30", "othera"].reduce((s, b) => s + (rep.aging[b].mbs || 0) + (rep.aging[b].mcorp || 0), 0))}</div>
              </div>
              <div className="rounded-md border border-border px-3 py-2 bg-secondary/40">
                <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Coll %</div>
                <div className="font-mono text-sm">
                  {(() => { const out = ["d90", "d60", "d30", "othera"].reduce((s, b) => s + (rep.aging[b].mbs || 0) + (rep.aging[b].mcorp || 0), 0); return out ? ((rep.weekly_collection / out) * 100).toFixed(1) : "0.0"; })()}%
                </div>
              </div>
            </div>
          </Card>
        ))}
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
                <div className="text-[11px] font-semibold uppercase tracking-wider text-[#2563EB]">Purchase (MBS / MCORP)</div>
                <div className="flex items-center gap-3"><span className="text-xs w-12 text-muted-foreground">Value</span><div className="flex-1"><AmountPair value={b.purchase.value} prefix="₹" testidBase={`branch-${i}-purchase-value`} onChange={(fld, v) => update((f) => (f.branches[i].purchase.value[fld] = v))} /></div></div>
                <div className="flex items-center gap-3"><span className="text-xs w-12 text-muted-foreground">Tons</span><div className="flex-1"><AmountPair value={b.purchase.tons} testidBase={`branch-${i}-purchase-tons`} onChange={(fld, v) => update((f) => (f.branches[i].purchase.tons[fld] = v))} /></div></div>
              </div>
              <div className="space-y-3">
                <div className="text-[11px] font-semibold uppercase tracking-wider text-[#16A34A]">Sales (MBS / MCORP)</div>
                <div className="flex items-center gap-3"><span className="text-xs w-12 text-muted-foreground">Value</span><div className="flex-1"><AmountPair value={b.sales.value} prefix="₹" testidBase={`branch-${i}-sales-value`} onChange={(fld, v) => update((f) => (f.branches[i].sales.value[fld] = v))} /></div></div>
                <div className="flex items-center gap-3"><span className="text-xs w-12 text-muted-foreground">Tons</span><div className="flex-1"><AmountPair value={b.sales.tons} testidBase={`branch-${i}-sales-tons`} onChange={(fld, v) => update((f) => (f.branches[i].sales.tons[fld] = v))} /></div></div>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Quotation */}
      <Card className="p-6 shadow-none" data-testid="quotation-editor">
        <h3 className="text-base font-medium mb-4">Quotation Pipeline (counts)</h3>
        <div className="space-y-2.5 max-w-2xl">
          <div className="grid grid-cols-12 gap-2 text-[10px] uppercase tracking-wider text-muted-foreground">
            <span className="col-span-4">Stage</span><span className="col-span-4">MBS</span><span className="col-span-4">MCORP</span>
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
