import axios from "axios";

const BASE = process.env.REACT_APP_BACKEND_URL;
export const API = `${BASE}/api`;

const api = axios.create({ baseURL: API, withCredentials: true });

export function formatApiError(detail) {
  if (detail == null) return "Something went wrong. Please try again.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail.map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e))).filter(Boolean).join(" ");
  if (detail && typeof detail.msg === "string") return detail.msg;
  return String(detail);
}

// auth
export const apiLogin = (email, password) => api.post("/auth/login", { email, password }).then((r) => r.data);
export const apiLogout = () => api.post("/auth/logout").then((r) => r.data);
export const apiMe = () => api.get("/auth/me").then((r) => r.data);

// meetings
export const getMeetings = () => api.get("/meetings").then((r) => r.data);
export const getMeeting = (id) => api.get(`/meetings/${id}`).then((r) => r.data);
export const createMeeting = (body) => api.post("/meetings", body).then((r) => r.data);
export const updateMeeting = (id, body) => api.put(`/meetings/${id}`, body).then((r) => r.data);
export const deleteMeeting = (id) => api.delete(`/meetings/${id}`).then((r) => r.data);
export const getTrends = () => api.get("/analytics/trends").then((r) => r.data);
export const extractFile = (formData) =>
  api.post("/extract", formData, { headers: { "Content-Type": "multipart/form-data" } }).then((r) => r.data);

// users
export const listUsers = () => api.get("/users").then((r) => r.data);
export const createUser = (body) => api.post("/users", body).then((r) => r.data);
export const deleteUser = (id) => api.delete(`/users/${id}`).then((r) => r.data);

export default api;
