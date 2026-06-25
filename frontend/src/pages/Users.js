import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listUsers, createUser, deleteUser, formatApiError } from "@/lib/api";
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
import { Loader2, UserPlus, Trash2 } from "lucide-react";
import { toast } from "sonner";

function initials(name) {
  return (name || "?").split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase();
}

export default function Users() {
  const { data: users, isLoading } = useQuery({ queryKey: ["users"], queryFn: listUsers });
  const { user: me } = useAuth();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState({ name: "", email: "", password: "", role: "viewer" });

  const create = useMutation({
    mutationFn: createUser,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["users"] });
      toast.success("User created");
      setOpen(false);
      setDraft({ name: "", email: "", password: "", role: "viewer" });
    },
    onError: (e) => toast.error(formatApiError(e.response?.data?.detail) || "Failed to create user"),
  });

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
          <p className="text-sm text-muted-foreground mt-1">Admins manage data; viewers get read-only dashboards.</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button data-testid="add-user-button"><UserPlus className="h-4 w-4" /> Add User</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>Create User</DialogTitle></DialogHeader>
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
                <Label className="text-xs uppercase tracking-wider text-muted-foreground">Password</Label>
                <Input type="password" value={draft.password} onChange={(e) => setDraft({ ...draft, password: e.target.value })} data-testid="user-password-input" />
              </div>
              <div className="space-y-2">
                <Label className="text-xs uppercase tracking-wider text-muted-foreground">Role</Label>
                <Select value={draft.role} onValueChange={(v) => setDraft({ ...draft, role: v })}>
                  <SelectTrigger data-testid="user-role-select"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="viewer">Viewer (read-only)</SelectItem>
                    <SelectItem value="admin">Admin (full access)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
              <Button onClick={() => create.mutate(draft)} disabled={create.isPending || !draft.name || !draft.email || !draft.password} data-testid="submit-user-button">
                {create.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Create"}
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
                    <div className="text-xs text-muted-foreground">{u.email}</div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Badge variant="outline" className={`uppercase text-[10px] tracking-wider ${u.role === "admin" ? "border-black text-black" : "text-muted-foreground"}`}>
                    {u.role}
                  </Badge>
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
