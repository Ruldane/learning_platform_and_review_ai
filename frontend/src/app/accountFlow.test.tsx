import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient } from "@tanstack/react-query";
import { createMemoryRouter, Outlet, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";
import { DataPage } from "@/features/account/pages/DataPage";
import { accountKeys, AUTH_SCOPE } from "@/features/account/queryKeys";
import { authKeys } from "@/features/auth/queryKeys";
import { SessionGate } from "@/features/auth/SessionGate";
import { accountApi } from "@/test/accountApi";
import { authApi, camille } from "@/test/authApi";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";

describe("« Delete everything » avec la porte de connexion", () => {
  it("shares the identity query key with the auth feature", () => {
    expect(accountKeys.me).toEqual(authKeys.me);
    expect(AUTH_SCOPE).toBe(authKeys.me[0]);
  });

  it("a 401 during the deletion leads once to /login, through the gate", async () => {
    server.use(...accountApi({ delete: "expired" }).handlers, ...authApi({ me: camille }).handlers);
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false, staleTime: 15_000 } },
    });
    const router = createMemoryRouter(
      [
        { path: "/login", element: <p>Sign in</p> },
        {
          path: "/",
          element: (
            <SessionGate>
              <Outlet />
            </SessionGate>
          ),
          children: [{ path: "settings/data", element: <DataPage /> }],
        },
      ],
      { initialEntries: ["/settings/data"] },
    );
    const Wrapper = createQueryWrapper(client);
    render(
      <Wrapper>
        <RouterProvider router={router} />
      </Wrapper>,
    );
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("Type SUPPRIMER to confirm"), "SUPPRIMER");
    await user.click(screen.getByRole("button", { name: "Delete everything" }));
    expect(await screen.findByText("Sign in")).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/login");
  });
});
