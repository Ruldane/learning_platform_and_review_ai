import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "@/app/App";
import { FEATURES } from "@/app/registry";
import { buildRouter } from "@/app/router";
import "./index.css";

if (import.meta.env.PROD && "serviceWorker" in navigator) {
  void navigator.serviceWorker.register("/mobile-worker.js").catch(() => undefined);
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App router={buildRouter(FEATURES)} />
  </StrictMode>,
);
