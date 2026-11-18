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
  it("ne porte que les menus, centrés : le nom et les infos sont dans le panneau de gauche", () => {
    render(
      <MemoryRouter>
        <Topbar menus={<nav>Menus</nav>} />
      </MemoryRouter>,
      { wrapper: createQueryWrapper() },
    );
    const banner = screen.getByRole("banner");
    expect(screen.getByRole("navigation")).toHaveTextContent("Menus");
    expect(banner.className).toContain("justify-center");
    expect(banner).not.toHaveTextContent("Tremplin");
    expect(screen.queryByRole("link", { name: "Tremplin" })).toBeNull();
  });

  it("garde le nom en simple texte et les emplacements sans menus (page nue)", () => {
    // Le compte connecté (emplacement `topbar` de la feature `auth`) lit `me` ; la série d'étude
    // (feature `study`) lit son résumé.
    server.use(
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
        <Topbar />
      </MemoryRouter>,
      { wrapper: createQueryWrapper() },
    );
    expect(screen.getByRole("banner")).toHaveTextContent("Tremplin");
    expect(screen.queryByRole("link", { name: "Tremplin" })).toBeNull();
  });
});
