import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { apiBaseUrl } from "@/shared/api/client";
import { authApi, camille } from "@/test/authApi";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { Topbar } from "./Topbar";

describe("Topbar", () => {
  it("affiche le nom (lien vers l'accueil), le voyant et les menus", () => {
    // La série d'étude (emplacement `topbar` de la feature `study`) lit son résumé.
    server.use(
      // Le compte connecté (emplacement `topbar` de la feature `auth`) lit `me`.
      ...authApi({ me: camille }).handlers,
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
    render(
      <MemoryRouter>
        <Topbar health={<span>Voyant</span>} menus={<nav>Menus</nav>} />
      </MemoryRouter>,
      { wrapper: createQueryWrapper() },
    );
    expect(screen.getByRole("link", { name: "Tremplin" })).toHaveAttribute("href", "/");
    expect(screen.getByText("Voyant")).toBeInTheDocument();
    expect(screen.getByRole("navigation")).toHaveTextContent("Menus");
  });

  it("garde le nom en simple texte sans menus (page nue)", () => {
    server.use(...authApi({ me: camille }).handlers);
    render(
      <MemoryRouter>
        <Topbar />
      </MemoryRouter>,
      { wrapper: createQueryWrapper() },
    );
    expect(screen.getByRole("banner")).toHaveTextContent("Tremplin");
    expect(screen.queryByRole("link", { name: "Tremplin" })).toBeNull();
  });
});
