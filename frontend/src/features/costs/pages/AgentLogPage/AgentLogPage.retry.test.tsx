import { QueryClient } from "@tanstack/react-query";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";
import { callPage, costsApi } from "@/test/costsApi";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { AgentLogPage } from "./AgentLogPage";

const broken = () =>
  HttpResponse.json(
    { error: { code: "boom", message: "Le serveur ne répond pas.", details: null } },
    { status: 500 },
  );

function setup(failing: { value: boolean }) {
  const api = costsApi({ calls: (url) => (failing.value ? broken() : callPage(url)) });
  server.use(...api.handlers);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createMemoryRouter([{ path: "/reglages/journal", element: <AgentLogPage /> }], {
    initialEntries: ["/reglages/journal"],
  });
  render(<RouterProvider router={router} />, { wrapper: createQueryWrapper(client) });
  return { ...api, client, user: userEvent.setup() };
}

describe("AgentLogPage, « Réessayer » reads what failed", () => {
  it("a failed read of the next page is read again with the same cursor", async () => {
    const failing = { value: false };
    const { callRequests, user } = setup(failing);
    await screen.findByText("2 appels affichés");
    failing.value = true;
    await user.click(screen.getByRole("button", { name: "Voir plus" }));
    expect(await screen.findByText("Le serveur ne répond pas.")).toBeInTheDocument();
    failing.value = false;
    await user.click(screen.getByRole("button", { name: "Réessayer" }));
    await screen.findByText("3 appels affichés");
    const retried = callRequests.at(-1)!;
    expect(retried.searchParams.get("before")).not.toBeNull();
  });

  it("a failed read of the first page, when pages are shown, reads the first page again", async () => {
    const failing = { value: false };
    const { callRequests, client, user } = setup(failing);
    await screen.findByText("2 appels affichés");
    failing.value = true;
    await act(async () => {
      await client.refetchQueries();
    });
    expect(await screen.findByText("Le serveur ne répond pas.")).toBeInTheDocument();
    failing.value = false;
    await user.click(screen.getByRole("button", { name: "Réessayer" }));
    await screen.findByText("2 appels affichés");
    expect(screen.queryByText("Le serveur ne répond pas.")).toBeNull();
    // Rien n'a été lu au-delà de la première page : « Réessayer » n'a pas demandé la suivante.
    expect(callRequests.at(-1)!.searchParams.get("before")).toBeNull();
    expect(screen.getByRole("button", { name: "Voir plus" })).toBeInTheDocument();
  });
});
