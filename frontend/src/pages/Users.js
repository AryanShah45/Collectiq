import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listUsers, createUser, updateUser, deleteUser, formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Loader2, UserPlus, Trash2, Pencil } from "lucide-react";
import { toast } from "sonner";

function initials(name) {
  return (name || "?").split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase();
}

export default function Users() {
  const { data: users, isLoading } = useQuery({ queryKey: ["users"], queryFn: listUsers });
  const { user: me, settings } = useAuth();
  const repOptions = settings?.collection_reps || [];
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null); // user object when editing, null when creating
  const blank = { name: "", email: "", password: "", role: "viewer", rep_name: "" };
  const [draft, setDraft] = useState(blank);

  const startCreate = () => { setEditing(null); setDraft(blank); setOpen(true); };
  const startEdit = (u) => {
    setEditing(u);
    setDraft({ name: u.name, email: u.email, password: "", role: u.role, rep_name: u.rep_name || "" });
    setOpen(true);
  };

  const create = useMutation({
    mutationFn: createUser,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["users"] });
      toast.success("User created");
      setOpen(false);
      setDraft(blank);
    },
    onError: (e) => toast.error(formatApiError(e.response?.data?.detail) || "Failed to create user"),
  });

  const update = useMutation({
    mutationFn: updateUser,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["users"] });
      toast.success("User updated");
      setOpen(false);
      setEditing(null);
      setDraft(blank);
    },
    onError: (e) => toast.error(formatApiError(e.response?.data?.detail) || "Failed to update user"),
  });

  const submit = () => {
    if (editing) update.mutate({ id: editing.id, ...draft });
    else create.mutate(draft);
  };
  const busy = create.isPending || update.isPending;

  const del = useMutation({
    mutationFn: deleteUser,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["users"] }); toast.success("User removed"); },
    onError: (e) => toast.error(formatApiError(e.response?.data?.detail) || "Failed to remove user"),
  });

  return (
    <div className="space-y-6" data-testid="users-page">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground mb-1">Access Control</div>
          <h1 className="text-3xl font-semibold tracking-tighter">Users</h1>
          <p className="text-sm text-muted-foreground mt-1">Admins manage everything · viewers get read-only dashboards · employees see only their own numbers.</p>
        </div>
        <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) setEditing(null); }}>
          <DialogTrigger asChild>
            <Button data-testid="add-user-button" onClick={startCreate}><UserPlus className="h-4 w-4" /> Add User</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>{editing ? `Edit ${editing.name}` : "Create User"}</DialogTitle></DialogHeader>
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <Label className="text-xs uppercase tracking-wider text-muted-foreground">Name</Label>
                <Input value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} data-testid="user-name-input" />
              </div>
              <div className="space-y-2">
                <Label className="text-xs uppercase tracking-wider text-muted-foreground">Email</Label>
                <Input type="email" value={draft.email} onChange={(e) => setDraft({ ...draft, email: e.target.value })} data-testid="user-email-input" />
              </div>
              <div className="space-y-2">
                <Label className="text-xs uppercase tracking-wider text-muted-foreground">{editing ? "New Password" : "Password"}</Label>
                <Input type="password" value={draft.password} placeholder={editing ? "Leave blank to keep the current password" : ""}
                       onChange={(e) => setDraft({ ...draft, password: e.target.value })} data-testid="user-password-input" />
              </div>
              <div className="space-y-2">
                <Label className="text-xs uppercase tracking-wider text-muted-foreground">Role</Label>
                <Select value={draft.role} onValueChange={(v) => setDraft({ ...draft, role: v, rep_name: v === "employee" ? draft.rep_name : "" })}
                        disabled={!!editing && editing.id === me?.id}>
                  <SelectTrigger data-testid="user-role-select"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="admin">Admin — full access (enter data, manage users)</SelectItem>
                    <SelectItem value="viewer">Viewer — read-only dashboards</SelectItem>
                    <SelectItem value="employee">Employee — own performance only</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              {draft.role === "employee" && (
                <div className="space-y-2">
                  <Label className="text-xs uppercase tracking-wider text-muted-foreground">Linked Representative</Label>
                  {repOptions.length ? (
                    <Select value={draft.rep_name} onValueChange={(v) => setDraft({ ...draft, rep_name: v })}>
                      <SelectTrigger data-testid="user-rep-select"><SelectValue placeholder="Pick their name from the roster" /></SelectTrigger>
                      <SelectContent>
                        {repOptions.map((n) => <SelectItem key={n} value={n}>{n}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  ) : (
                    <Input value={draft.rep_name} placeholder="Representative name (as entered in meetings)"
                           onChange={(e) => setDraft({ ...draft, rep_name: e.target.value })} data-testid="user-rep-input" />
                  )}
                  <p className="text-[11px] text-muted-foreground">They will only see the numbers recorded under this name.</p>
                </div>
              )}
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
              <Button onClick={submit}
                      disabled={busy || !draft.name || !draft.email || (!editing && !draft.password) || (draft.role === "employee" && !draft.rep_name)}
                      data-testid="submit-user-button">
                {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : editing ? "Save Changes" : "Create"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <Card className="shadow-none p-2">
        {isLoading ? (
          <div className="flex items-center justify-center py-20"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
        ) : (
          <div className="divide-y divide-border">
            {users?.map((u) => (
              <div key={u.id} className="flex items-center justify-between px-4 py-3" data-testid={`user-row-${u.email}`}>
                <div className="flex items-center gap-3">
                  <Avatar className="h-9 w-9 border border-border">
                    <AvatarFallback className="bg-black text-white text-xs">{initials(u.name)}</AvatarFallback>
                  </Avatar>
                  <div>
                    <div className="text-sm font-medium flex items-center gap-2">
                      {u.name}
                      {u.id === me?.id && <span className="text-[10px] text-muted-foreground">(you)</span>}
                    </div>
                    <div className="text-xs text-muted-foreground">{u.email}{u.rep_name ? ` · linked to ${u.rep_name}` : ""}</div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Badge variant="outline" className={`uppercase text-[10px] tracking-wider ${u.role === "admin" ? "border-black text-black" : "text-muted-foreground"}`}>
                    {u.role}
                  </Badge>
                  <Button variant="ghost" size="icon" onClick={() => startEdit(u)} data-testid={`edit-user-${u.email}`}>
                    <Pencil className="h-4 w-4" />
                  </Button>
                  {u.id !== me?.id && (
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <Button variant="ghost" size="icon" className="text-[#DC2626]" data-testid={`delete-user-${u.email}`}>
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>Remove {u.name}?</AlertDialogTitle>
                          <AlertDialogDescription>They will lose access immediately.</AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>Cancel</AlertDialogCancel>
                          <AlertDialogAction className="bg-[#DC2626] hover:bg-[#DC2626]/90" onClick={() => del.mutate(u.id)}>Remove</AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
