import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { formatApiError } from "@/lib/api";
import { Activity, Loader2, ShieldCheck } from "lucide-react";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("admin@company.com");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      navigate("/");
    } catch (err) {
      setError(formatApiError(err.response?.data?.detail) || err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-background">
      {/* Left brand panel */}
      <div className="hidden lg:flex flex-col justify-between bg-black text-white p-12">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-md bg-white flex items-center justify-center">
            <Activity className="h-6 w-6 text-black" strokeWidth={2.5} />
          </div>
          <div>
            <div className="font-semibold text-lg tracking-tight">COLLECTIQ</div>
            <div className="text-[10px] uppercase tracking-[0.3em] text-white/50">Collection Intelligence</div>
          </div>
        </div>
        <div className="space-y-6">
          <h1 className="text-4xl xl:text-5xl font-semibold tracking-tighter leading-[1.05]">
            Turn your weekly<br />collection meeting<br />into decisions.
          </h1>
          <p className="text-white/60 max-w-md leading-relaxed">
            Aging analysis across 90 / 60 / 30 days, two companies side by side, rep leaderboards,
            quotation pipeline and week-over-week trends — all in one control room.
          </p>
          <div className="flex flex-wrap gap-2 pt-2">
            {["90-Day Aging", "Two-company view", "Rep Leaderboard", "Quotation Funnel", "Trends"].map((t) => (
              <span key={t} className="text-xs px-3 py-1 rounded-full border border-white/20 text-white/70">{t}</span>
            ))}
          </div>
        </div>
        <div className="text-xs text-white/40 flex items-center gap-2">
          <ShieldCheck className="h-3.5 w-3.5" /> Role-based access · Admin &amp; Viewer
        </div>
      </div>

      {/* Right form */}
      <div className="flex items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-sm">
          <div className="lg:hidden flex items-center gap-2.5 mb-8">
            <div className="h-9 w-9 rounded-md bg-black flex items-center justify-center">
              <Activity className="h-5 w-5 text-white" strokeWidth={2.5} />
            </div>
            <span className="font-semibold tracking-tight">COLLECTIQ</span>
          </div>
          <h2 className="text-2xl font-semibold tracking-tight">Sign in</h2>
          <p className="text-sm text-muted-foreground mt-1 mb-8">Access your collection dashboard.</p>

          <form onSubmit={submit} className="space-y-5" data-testid="login-form">
            <div className="space-y-2">
              <Label htmlFor="email" className="text-xs uppercase tracking-wider text-muted-foreground">Email</Label>
              <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                     required data-testid="login-email" autoComplete="username" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password" className="text-xs uppercase tracking-wider text-muted-foreground">Password</Label>
              <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                     required data-testid="login-password" autoComplete="current-password" placeholder="••••••••" />
            </div>
            {error && (
              <div className="text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-md px-3 py-2" data-testid="login-error">
                {error}
              </div>
            )}
            <Button type="submit" className="w-full" disabled={loading} data-testid="login-submit">
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Sign in"}
            </Button>
          </form>

          <div className="mt-8 text-xs text-muted-foreground border border-border rounded-md p-4 bg-secondary/40">
            <div className="font-medium text-foreground mb-1">Demo accounts</div>
            <div>Admin — admin@company.com / Admin@123</div>
            <div>Viewer — viewer@company.com / Viewer@123</div>
          </div>
        </div>
      </div>
    </div>
  );
}
