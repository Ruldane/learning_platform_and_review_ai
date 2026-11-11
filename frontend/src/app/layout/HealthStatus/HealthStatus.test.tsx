import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { apiBaseUrl } from "@/shared/api/client";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { HealthStatus } from "./HealthStatus";

const HEALTH_URL = `${apiBaseUrl}/api/v1/health`;

describe("HealthStatus", () => {
  it("branche useHealth sur le voyant", async () => {
    server.use(http.get(HEALTH_URL, () => HttpResponse.json({ status: "ok", checks: {} })));
    render(<HealthStatus />, { wrapper: createQueryWrapper() });
    expect(await screen.findByText("Tous les services répondent")).toBeInTheDocument();
  });

  it("signale un serveur injoignable", async () => {
    server.use(http.get(HEALTH_URL, () => new HttpResponse("boom", { status: 500 })));
    render(<HealthStatus />, { wrapper: createQueryWrapper() });
    expect(await screen.findByText("Serveur injoignable")).toBeInTheDocument();
  });
});
