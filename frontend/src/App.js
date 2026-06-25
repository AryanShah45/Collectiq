import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "@/context/AuthContext";
import { Toaster } from "@/components/ui/sonner";
import ProtectedRoute from "@/components/ProtectedRoute";
import Layout from "@/components/Layout";
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import Trends from "@/pages/Trends";
import Meetings from "@/pages/Meetings";
import DataEntry from "@/pages/DataEntry";
import Users from "@/pages/Users";

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
          <Route path="/login" element={<Login />} />
          <Route path="/" element={withLayout(<Dashboard />)} />
          <Route path="/trends" element={withLayout(<Trends />)} />
          <Route path="/meetings" element={withLayout(<Meetings />)} />
          <Route path="/data-entry" element={withAdminLayout(<DataEntry />)} />
          <Route path="/users" element={withAdminLayout(<Users />)} />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" richColors />
    </AuthProvider>
  );
}
