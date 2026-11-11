import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiBaseUrl } from "@/shared/api/client";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { completed, interrupt, started, tok } from "@/shared/realtime/testEvents";
import { createFakeSocketServer } from "@/test/fakeSocket";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { DemoDebatePage } from "./DemoDebatePage";

const API = `${apiBaseUrl}/api/v1/sessions`;
const view = (status: string) => ({ session_id: "s1", status, last_seq: 0 });
const choiceInterrupt = {
  ...interrupt(3, "i1"),
  payload: {
    interrupt_id: "i1",
    kind: "choice" as const,
    question: "Quel angle pour le second tour ?",
    options: [
      { label: "Plus concret", value: "concret" },
      { label: "Plus court", value: "court" },
    ],
  },
};

function setup(route = "/demo") {
  const fake = createFakeSocketServer();
  const router = createMemoryRouter(
    [{ path: "/demo", element: <DemoDebatePage createSocket={fake.factory} /> }],
    { initialEntries: [route] },
  );
  render(<RouterProvider router={router} />, { wrapper: createQueryWrapper() });
  return { fake, router, user: userEvent.setup() };
}

async function startDebate(user: ReturnType<typeof userEvent.setup>, topic = "apprendre Rust") {
  await user.type(screen.getByLabelText("Sujet"), topic);
  await user.click(screen.getByRole("button", { name: "Lancer le débat" }));
}

describe("DemoDebatePage", () => {
  beforeEach(() => useSessionStore.getState().reset("s1"));
  afterEach(() => useSessionStore.getState().reset("s1"));

  it("starts a debate, streams turns and answers the interrupt", async () => {
    const posted: unknown[] = [];
    const resumed: unknown[] = [];
    server.use(
      http.post(API, async ({ request }) => {
        posted.push(await request.json());
        return HttpResponse.json({ session_id: "s1" }, { status: 201 });
      }),
      http.post(`${API}/s1/resume`, async ({ request }) => {
        resumed.push(await request.json());
        return HttpResponse.json(view("running"));
      }),
    );
    const { fake, router, user } = setup();
    await startDebate(user);
    await waitFor(() => expect(fake.sockets).toHaveLength(1));
    expect(posted).toEqual([{ graph: "demo_debate", input: { topic: "apprendre Rust" } }]);
    expect(router.state.location.search).toBe("?session=s1");

    fake
      .last()
      .open()
      .push(started(1, "demo_proponent"), tok(2, "m1", "Oui", "demo_proponent"));
    fake.last().push(choiceInterrupt);
    expect(await screen.findByText("Oui")).toBeInTheDocument();
    expect(screen.getByText("Avocat")).toBeInTheDocument();
    await user.click(await screen.findByRole("button", { name: "Plus concret" }));
    await waitFor(() => expect(resumed).toEqual([{ interrupt_id: "i1", value: "concret" }]));
    expect(await screen.findByText("Réponse envoyée")).toBeInTheDocument();
  });

  it("rejoint la session de l'URL après un rechargement, sans formulaire", async () => {
    const { fake } = setup("/demo?session=s1");
    expect(screen.queryByLabelText("Sujet")).not.toBeInTheDocument();
    await waitFor(() => expect(fake.sockets).toHaveLength(1));
    expect(fake.last().url).toContain("/sessions/s1/stream?after_seq=0");
    fake
      .last()
      .open()
      .push(started(1, "demo_critic"), tok(2, "m1", "Mais encore ?"));
    expect(await screen.findByText("Mais encore ?")).toBeInTheDocument();
  });

  it("montre une session introuvable avec ErrorState", async () => {
    const { fake } = setup("/demo?session=s1");
    await waitFor(() => expect(fake.sockets).toHaveLength(1));
    fake.last().open().drop(4404);
    expect(await screen.findByRole("alert")).toHaveTextContent("Cette session est introuvable.");
  });

  it("affiche l'erreur de lancement et garde le formulaire", async () => {
    server.use(
      http.post(API, () =>
        HttpResponse.json({ code: "llm_key_missing", message: "Clé manquante." }, { status: 422 }),
      ),
    );
    const { user } = setup();
    await startDebate(user);
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByLabelText("Sujet")).toBeInTheDocument();
  });

  it("demande confirmation dans la page avant d'annuler", async () => {
    const cancelled = vi.fn();
    server.use(
      http.post(`${API}/s1/cancel`, () => {
        cancelled();
        return HttpResponse.json(view("cancelled"));
      }),
    );
    const confirm = vi.spyOn(window, "confirm");
    const { fake, user } = setup("/demo?session=s1");
    await waitFor(() => expect(fake.sockets).toHaveLength(1));
    fake
      .last()
      .open()
      .push(started(1, "demo_proponent"), tok(2, "m1", "Oui"));
    await user.click(await screen.findByRole("button", { name: "Annuler" }));
    expect(cancelled).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Non, continuer" }));
    expect(screen.queryByText("Annuler le débat ?")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Annuler" }));
    await user.click(screen.getByRole("button", { name: "Oui, annuler le débat" }));
    await waitFor(() => expect(cancelled).toHaveBeenCalledTimes(1));
    expect(confirm).not.toHaveBeenCalled();
    expect(await screen.findByText("Annulée")).toBeInTheDocument();
  });

  it("envoie un message à l'équipe", async () => {
    const messages: unknown[] = [];
    server.use(
      http.post(`${API}/s1/message`, async ({ request }) => {
        messages.push(await request.json());
        return HttpResponse.json({});
      }),
    );
    const { fake, user } = setup("/demo?session=s1");
    await waitFor(() => expect(fake.sockets).toHaveLength(1));
    fake.last().open().push(started(1, "demo_proponent"), choiceInterrupt);
    await user.type(await screen.findByLabelText("Ton message"), "Pense aux débutants{Enter}");
    await waitFor(() => expect(messages).toEqual([{ text: "Pense aux débutants" }]));
  });

  it("propose un nouveau débat une fois la session terminée", async () => {
    server.use(http.get(`${API}/s1`, () => HttpResponse.json(view("completed"))));
    const { fake, router, user } = setup("/demo?session=s1");
    await waitFor(() => expect(fake.sockets).toHaveLength(1));
    fake.last().open().push(started(1, "demo_proponent"), completed(2)).drop(1000);
    await user.click(await screen.findByRole("button", { name: "Nouveau débat" }));
    expect(await screen.findByLabelText("Sujet")).toBeInTheDocument();
    expect(router.state.location.search).toBe("");
  });
});
