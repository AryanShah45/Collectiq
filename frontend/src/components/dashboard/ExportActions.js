import { useState } from "react";
import { exportMeetingFile, pushMeetingToNotion, formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { FileText, Sheet, Loader2, Send } from "lucide-react";
import { toast } from "sonner";

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click(); a.remove();
  URL.revokeObjectURL(url);
}

export default function ExportActions({ meeting }) {
  const { isAdmin } = useAuth();
  const [busy, setBusy] = useState("");
  const date = meeting?.meeting_date || "report";

  const doExport = async (fmt) => {
    setBusy(fmt);
    try {
      const blob = await exportMeetingFile(meeting.id, fmt);
      downloadBlob(blob, `collectiq-${date}.${fmt}`);
      toast.success(`${fmt.toUpperCase()} downloaded`);
    } catch {
      toast.error(`Could not generate ${fmt.toUpperCase()}`);
    } finally {
      setBusy("");
    }
  };

  const syncNotion = async () => {
    setBusy("notion");
    try {
      const res = await pushMeetingToNotion(meeting.id);
      toast.success("Sent to Notion");
      if (res?.url) window.open(res.url, "_blank");
    } catch (e) {
      toast.error(formatApiError(e.response?.data?.detail) || "Notion sync failed — check Roster › Notion setup");
    } finally {
      setBusy("");
    }
  };

  return (
    <div className="flex items-center gap-2">
      <Button variant="outline" size="sm" onClick={() => doExport("pdf")} disabled={!!busy} data-testid="export-pdf">
        {busy === "pdf" ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileText className="h-4 w-4" />} PDF
      </Button>
      <Button variant="outline" size="sm" onClick={() => doExport("xlsx")} disabled={!!busy} data-testid="export-xlsx">
        {busy === "xlsx" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sheet className="h-4 w-4" />} Excel
      </Button>
      {isAdmin && (
        <Button variant="outline" size="sm" onClick={syncNotion} disabled={!!busy} data-testid="sync-notion">
          {busy === "notion" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />} Notion
        </Button>
      )}
    </div>
  );
}
