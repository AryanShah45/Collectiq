// Local dev only: forward same-origin /api requests to the FastAPI backend so
// the browser-resolved API base (window.location.origin + "/api") works when
// running `craco start`. Not used in production (nginx handles /api there).
const { createProxyMiddleware } = require("http-proxy-middleware");

module.exports = function (app) {
  app.use(
    "/api",
    createProxyMiddleware({
      target: process.env.BACKEND_PROXY_TARGET || "http://localhost:8000",
      changeOrigin: true,
    })
  );
};
