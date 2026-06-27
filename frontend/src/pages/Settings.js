import { useEffect, useState, useRef } from "react";
import { useMutation } from "@tanstack/react-query";
import { useQueryClient } from "@tanstack/react-query";
import { updateSettings, getBackup, restoreBackup, getNotionStatus, saveNotionConfig, formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Loader2, Plus, Trash2, Save, Users2, Megaphone, Boxes, Building2, Download, Upload, Database, BookText, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";

function NameList({ icon: Icon, title, hint, items, setItems, testid }) {
  const add = () => setItems([...items, ""]);
  const setAt = (i, v) => setItems(items.map((x, j) => (j === i ? v : x)));
  const removeAt = (i) => setItems(items.filter((_, j) => j !== i));
  return (
    <Card className="p-6 shadow-none" data-testid={testid}>
      <div className="flex items-center justify-between mb-1">
        <h3 className="text-lg font-medium flex items-center gap-2"><Icon className="h-5 w-5" /> {title} ({items.length})</h3>
        <Button variant="secondary" size="sm" onClick={add} data-testid={`${testid}-add`}><Plus className="h-4 w-4" /> Add</Button>
      </div>
      <p className="text-xs text-muted-foreground mb-4">{hint}</p>
      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground italic py-2">None yet — click Add to create the first one.</p>
      ) : (
        <div className="space-y-2">
          {items.map((name, i) => (
            <div key={i} className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground w-6 text-right">{i + 1}.</span>
              <Input value={name} placeholder="Name" className="max-w-sm" onChange={(e) => setAt(i, e.target.value)} data-testid={`${testid}-input-${i}`} />
              <Button variant="ghost" size="icon" className="text-[#DC2626]" onClick={() => removeAt(i)} data-testid={`${testid}-remove-${i}`}><Trash2 className="h-4 w-4" /></Button>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

export default function Settings() {
  const { settings, refreshSettings } = useAuth();
  const [companyA, setCompanyA] = useState("MBS");
  const [companyB, setCompanyB] = useState("MCORP");
  const [collectionReps, setCollectionReps] = useState([]);
  const [marketingReps, setMarketingReps] = useState([]);
  const [branches, setBranches] = useState([]);
  const [ready, setReady] = useState(false);

  // Seed local draft from settings once they load.
  useEffect(() => {
    if (settings && !ready) {
      setCompanyA(settings.company_a || "MBS");
      setCompanyB(settings.company_b || "MCORP");
      setCollectionReps(settings.collection_reps || []);
      setMarketingReps(settings.marketing_reps || []);
      setBranches(settings.branches || []);
      setReady(true);
    }
  }, [settings, ready]);

  const save = useMutation({
    mutationFn: () => updateSettings({
      company_a: companyA, company_b: companyB,
      collection_reps: collectionReps, marketing_reps: marketingReps, branches,
    }),
    onSuccess: async () => {
      await refreshSettings();
      toast.success("Roster & settings saved");
    },
    onError: (e) => toast.error(formatApiError(e.response?.data?.detail) || "Failed to save"),
  });

  const qc = useQueryClient();
  const fileRef = useRef(null);

  // Notion config
  const [notion, setNotion] = useState({ connected: false, database_id: "", via_env: false });
  const [notionToken, setNotionToken] = useState("");
  const [notionDb, setNotionDb] = useState("");
  useEffect(() => {
    getNotionStatus().then((st) => { setNotion(st); setNotionDb(st.database_id || ""); }).catch(() => {});
  }, []);
  const saveNotion = useMutation({
    mutationFn: () => saveNotionConfig({ token: notionToken, database_id: notionDb }),
    onSuccess: async () => {
      setNotionToken("");
      const st = await getNotionStatus(); setNotion(st);
      toast.success("Notion settings saved");
    },
    onError: (e) => toast.error(formatApiError(e.response?.data?.detail) || "Failed to save Notion settings"),
  });

  const downloadBackup = async () => {
    try {
      const data = await getBackup();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      const stamp = new Date().toISOString().slice(0, 10);
      a.href = url; a.download = `collectiq-backup-${stamp}.json`;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
      toast.success("Backup downloaded");
    } catch (e) {
      toast.error("Could not create backup");
    }
  };

  const onRestoreFile = (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async () => {
      try {
        const data = JSON.parse(reader.result);
        const res = await restoreBackup(data);
        await refreshSettings();
        qc.invalidateQueries();
        toast.success(`Restored ${res.restored_meetings} meeting(s)`);
        setReady(false); // re-seed local draft from restored settings
      } catch (err) {
        toast.error(formatApiError(err.response?.data?.detail) || "Invalid backup file");
      }
    };
    reader.readAsText(file);
  };

  return (
    <div className="space-y-6" data-testid="settings-page">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground mb-1">Configuration</div>
          <h1 className="text-3xl font-semibold tracking-tighter">Roster &amp; Settings</h1>
          <p className="text-sm text-muted-foreground mt-1">Set your company names and the people &amp; branches that appear in every weekly entry.</p>
        </div>
        <Button onClick={() => save.mutate()} disabled={save.isPending} data-testid="save-settings-button">
          {save.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} Save
        </Button>
      </div>

      <Card className="p-6 shadow-none" data-testid="company-names-card">
        <h3 className="text-lg font-medium flex items-center gap-2 mb-1"><Building2 className="h-5 w-5" /> Company Names</h3>
        <p className="text-xs text-muted-foreground mb-4">The two businesses tracked side by side. These labels appear across every dashboard, table and form.</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-xl">
          <div className="space-y-2">
            <Label className="text-xs uppercase tracking-wider text-muted-foreground">Company A</Label>
            <Input value={companyA} onChange={(e) => setCompanyA(e.target.value)} data-testid="company-a-input" />
          </div>
          <div className="space-y-2">
            <Label className="text-xs uppercase tracking-wider text-muted-foreground">Company B</Label>
            <Input value={companyB} onChange={(e) => setCompanyB(e.target.value)} data-testid="company-b-input" />
          </div>
        </div>
      </Card>

      <Separator />

      <NameList icon={Users2} title="Collection Representatives" testid="roster-collection"
                hint="People who handle collections. Each one becomes a pre-filled row when you create a new weekly entry."
                items={collectionReps} setItems={setCollectionReps} />

      <NameList icon={Megaphone} title="Marketing Representatives" testid="roster-marketing"
                hint="People tracked in the marketing section (visits, inquiries, order loss, targets)."
                items={marketingReps} setItems={setMarketingReps} />

      <NameList icon={Boxes} title="Branches" testid="roster-branches"
                hint="Branches tracked for sales & purchase (tonnage and value)."
                items={branches} setItems={setBranches} />

      <Separator />

      <Card className="p-6 shadow-none" data-testid="notion-card">
        <h3 className="text-lg font-medium flex items-center gap-2 mb-1"><BookText className="h-5 w-5" /> Notion Sync</h3>
        <p className="text-xs text-muted-foreground mb-4">
          Send every saved meeting into a Notion database automatically. Create an integration at
          notion.so/my-integrations, share your database with it, then paste the secret and the database ID below.
          {notion.via_env && " (Currently set via environment variables.)"}
        </p>
        <div className="flex items-center gap-2 mb-4 text-sm">
          {notion.connected
            ? <span className="inline-flex items-center gap-1.5 text-[#16A34A]"><CheckCircle2 className="h-4 w-4" /> Connected</span>
            : <span className="text-muted-foreground">Not connected</span>}
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-2xl">
          <div className="space-y-2">
            <Label className="text-xs uppercase tracking-wider text-muted-foreground">Integration Secret</Label>
            <Input type="password" value={notionToken} placeholder={notion.connected ? "•••••• (leave blank to keep)" : "secret_..."} onChange={(e) => setNotionToken(e.target.value)} data-testid="notion-token-input" />
          </div>
          <div className="space-y-2">
            <Label className="text-xs uppercase tracking-wider text-muted-foreground">Database ID</Label>
            <Input value={notionDb} placeholder="32-char database id" onChange={(e) => setNotionDb(e.target.value)} data-testid="notion-db-input" />
          </div>
        </div>
        <div className="mt-4">
          <Button variant="outline" onClick={() => saveNotion.mutate()} disabled={saveNotion.isPending} data-testid="save-notion-button">
            {saveNotion.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} Save Notion settings
          </Button>
        </div>
      </Card>

      <Separator />

      <Card className="p-6 shadow-none" data-testid="backup-card">
        <h3 className="text-lg font-medium flex items-center gap-2 mb-1"><Database className="h-5 w-5" /> Data &amp; Backup</h3>
        <p className="text-xs text-muted-foreground mb-4">
          Your data is stored safely and persists across restarts. Download a portable backup of everything
          (all weeks + this roster) any time, and restore it later or on another machine.
        </p>
        <div className="flex flex-wrap gap-3">
          <Button variant="outline" onClick={downloadBackup} data-testid="download-backup-button"><Download className="h-4 w-4" /> Download backup</Button>
          <Button variant="outline" onClick={() => fileRef.current?.click()} data-testid="restore-backup-button"><Upload className="h-4 w-4" /> Restore from backup</Button>
          <input ref={fileRef} type="file" accept="application/json,.json" className="hidden" onChange={onRestoreFile} />
        </div>
        <p className="text-[11px] text-muted-foreground mt-3">Restoring replaces all current meetings &amp; settings with the file's contents.</p>
      </Card>

      <div className="flex justify-end">
        <Button onClick={() => save.mutate()} disabled={save.isPending} data-testid="save-settings-button-bottom">
          {save.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} Save changes
        </Button>
      </div>
    </div>
  );
}
