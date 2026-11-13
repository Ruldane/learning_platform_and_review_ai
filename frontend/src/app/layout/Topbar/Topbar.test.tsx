import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { apiBaseUrl } from "@/shared/api/client";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { Topbar } from "./Topbar";

describe("Topbar", () => {
  it("affiche le nom de l'application et le contenu de droite", () => {
    // La série d'étude (emplacement `topbar` de la feature `study`) lit son résumé.
    server.use(
      http.get(`${apiBaseUrl}/api/v1/study-sessions/summary`, () =>
        HttpResponse.json({
          streak_days: 0,
          week_minutes: 0,
          work_minutes: 50,
          break_minutes: 10,
          open_session_id: null,
          block: null,
        }),
      ),
    );
    render(<Topbar right={<span>Voyant</span>} />, { wrapper: createQueryWrapper() });
    expect(screen.getByRole("banner")).toHaveTextContent("Tremplin");
    expect(screen.getByText("Voyant")).toBeInTheDocument();
  });
});
