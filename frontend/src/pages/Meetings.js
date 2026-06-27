import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { getMeetings, deleteMeeting } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { formatINR } from "@/lib/calc";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Loader2, Plus, Eye, Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";

function fmtDate(s) {
  if (!s) return "—";
  return new Date(s).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

export default function Meetings() {
  const { data: meetings, isLoading } = useQuery({ queryKey: ["meetings"], queryFn: getMeetings });
  const { isAdmin } = useAuth();
  const navigate = useNavigate();
  const qc = useQueryClient();

  const del = useMutation({
    mutationFn: deleteMeeting,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["meetings"] }); toast.success("Meeting deleted"); },
    onError: () => toast.error("Failed to delete meeting"),
  });

  return (
    <div className="space-y-6" data-testid="meetings-page">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground mb-1">Archive</div>
          <h1 className="text-3xl font-semibold tracking-tighter">Meetings</h1>
          <p className="text-sm text-muted-foreground mt-1">All recorded weekly collection reports.</p>
        </div>
        {isAdmin && (
          <Button onClick={() => navigate("/data-entry")} data-testid="new-meeting-button">
            <Plus className="h-4 w-4" /> New Meeting
          </Button>
        )}
      </div>

      <Card className="shadow-none overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center py-20"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="bg-secondary/50">
                <TableHead>Period</TableHead>
                <TableHead>Week</TableHead>
                <TableHead className="text-right">Total Outstanding</TableHead>
                <TableHead className="text-right">90-Day</TableHead>
                <TableHead className="text-right">Avg Coll %</TableHead>
                <TableHead>Recorded By</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {meetings?.map((m) => (
                <TableRow key={m.id} className="hover:bg-secondary/40" data-testid={`meeting-row-${m.id}`}>
                  <TableCell className="font-medium">{fmtDate(m.period_start)} – {fmtDate(m.period_end)}</TableCell>
                  <TableCell><Badge variant="outline" className="font-mono text-xs">{m.week_label}</Badge></TableCell>
                  <TableCell className="text-right font-mono tabular-nums">{formatINR(m.summary?.total_outstanding)}</TableCell>
                  <TableCell className="text-right font-mono tabular-nums text-[#DC2626]">{formatINR(m.summary?.d90)}</TableCell>
                  <TableCell className="text-right font-mono tabular-nums">{(m.summary?.coll_pct ?? 0).toFixed(1)}%</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{m.created_by}</TableCell>
                  <TableCell>
                    <div className="flex items-center justify-end gap-1">
                      <Button variant="ghost" size="icon" title="View" onClick={() => navigate(`/?meeting=${m.id}`)} data-testid={`view-meeting-${m.id}`}>
                        <Eye className="h-4 w-4" />
                      </Button>
                      {isAdmin && (
                        <>
                          <Button variant="ghost" size="icon" title="Edit" onClick={() => navigate(`/data-entry?id=${m.id}`)} data-testid={`edit-meeting-${m.id}`}>
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <AlertDialog>
                            <AlertDialogTrigger asChild>
                              <Button variant="ghost" size="icon" title="Delete" className="text-[#DC2626]" data-testid={`delete-meeting-${m.id}`}>
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent>
                              <AlertDialogHeader>
                                <AlertDialogTitle>Delete this meeting?</AlertDialogTitle>
                                <AlertDialogDescription>
                                  This permanently removes the report for {fmtDate(m.period_start)} – {fmtDate(m.period_end)}.
                                </AlertDialogDescription>
                              </AlertDialogHeader>
                              <AlertDialogFooter>
                                <AlertDialogCancel>Cancel</AlertDialogCancel>
                                <AlertDialogAction className="bg-[#DC2626] hover:bg-[#DC2626]/90" onClick={() => del.mutate(m.id)} data-testid={`confirm-delete-${m.id}`}>
                                  Delete
                                </AlertDialogAction>
                              </AlertDialogFooter>
                            </AlertDialogContent>
                          </AlertDialog>
                        </>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
              {!meetings?.length && (
                <TableRow><TableCell colSpan={7} className="text-center py-12 text-muted-foreground">No meetings recorded yet.</TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        )}
      </Card>
    </div>
  );
}
