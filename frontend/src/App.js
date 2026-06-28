import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "@/context/AuthContext";
import { Toaster } from "@/components/ui/sonner";
import ProtectedRoute from "@/components/ProtectedRoute";
import Layout from "@/components/Layout";
import Dashboard from "@/pages/Dashboard";
import Trends from "@/pages/Trends";
import Meetings from "@/pages/Meetings";
import DataEntry from "@/pages/DataEntry";
import Users from "@/pages/Users";
import Settings from "@/pages/Settings";

const withLayout = (el) => (
  <ProtectedRoute>
    <Layout>{el}</Layout>
  </ProtectedRoute>
);

const withAdminLayout = (el) => (
  <ProtectedRoute requireAdmin>
    <Layout>{el}</Layout>
  </ProtectedRoute>
);

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={withLayout(<Dashboard />)} />
          <Route path="/trends" element={withLayout(<Trends />)} />
          <Route path="/meetings" element={withLayout(<Meetings />)} />
          <Route path="/data-entry" element={withAdminLayout(<DataEntry />)} />
          <Route path="/users" element={withAdminLayout(<Users />)} />
          <Route path="/settings" element={withAdminLayout(<Settings />)} />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" richColors />
    </AuthProvider>
  );
}
