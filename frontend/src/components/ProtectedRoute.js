import { Navigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Loader2 } from "lucide-react";

export default function ProtectedRoute({ children, requireAdmin = false }) {
  const { user, isAdmin, refresh } = useAuth();

  if (user === null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background" data-testid="auth-loading">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }
  if (user === false) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 bg-background px-6 text-center" data-testid="session-error">
        <p className="text-sm text-muted-foreground max-w-sm">
          Couldn&apos;t reach the server to start your session. Please make sure the
          backend is running, then retry.
        </p>
        <button
          onClick={() => refresh()}
          className="px-4 py-2 rounded-md bg-black text-white text-sm font-medium"
          data-testid="session-retry"
        >
          Retry
        </button>
      </div>
    );
  }
  if (requireAdmin && !isAdmin) return <Navigate to="/" replace />;
  return children;
}
