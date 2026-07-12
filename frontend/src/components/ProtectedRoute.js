import { Navigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Loader2 } from "lucide-react";

export default function ProtectedRoute({ children, requireAdmin = false, allowEmployee = false }) {
  const { user, isAdmin, isEmployee } = useAuth();

  if (user === null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background" data-testid="auth-loading">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }
  if (user === false) return <Navigate to="/login" replace />;
  // Employees only get their personal page — never dashboards or admin pages.
  if (isEmployee && !allowEmployee) return <Navigate to="/my" replace />;
  if (requireAdmin && !isAdmin) return <Navigate to="/" replace />;
  return children;
}
