import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { API } from "@/test/councilApi";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { summaryOut } from "@/test/studyApi";
import { StudyTopbarSlot } from "./StudyTopbarSlot";

describe("StudyTopbarSlot", () => {
  it("shows streak and week hours in the top bar", async () => {
    server.use(
      http.get(`${API}/study-sessions/summary`, () =>
        HttpResponse.json(summaryOut({ streak_days: 5, week_minutes: 210 })),
      ),
    );
    render(<StudyTopbarSlot />, { wrapper: createQueryWrapper() });
    expect(await screen.findByText("Série : 5 jours")).toBeInTheDocument();
    expect(screen.getByText("Cette semaine : 3 h 30")).toBeInTheDocument();
  });

  it("says in one line that the figures are unavailable", async () => {
    server.use(
      http.get(`${API}/study-sessions/summary`, () =>
        HttpResponse.json(
          { error: { code: "boom", message: "Panne.", details: null } },
          { status: 500 },
        ),
      ),
    );
    render(<StudyTopbarSlot />, { wrapper: createQueryWrapper() });
    expect(await screen.findByText("Rythme d'étude indisponible")).toBeInTheDocument();
  });
});
