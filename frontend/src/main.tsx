import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "@/app/App";
import { FEATURES } from "@/app/registry";
import { buildRouter } from "@/app/router";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App router={buildRouter(FEATURES)} />
  </StrictMode>,
);
