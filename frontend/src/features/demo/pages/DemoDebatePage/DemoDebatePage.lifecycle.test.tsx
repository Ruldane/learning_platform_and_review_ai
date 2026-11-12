import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { apiBaseUrl } from "@/shared/api/client";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { completed, interrupt, message, started, tok, userMsg } from "@/shared/realtime/testEvents";
import type { InterruptPayload, SessionEvent } from "@/shared/realtime/types";
import { createFakeSocketServer } from "@/test/fakeSocket";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { DemoDebatePage } from "./DemoDebatePage";

const API = `${apiBaseUrl}/api/v1/sessions`;
const angle: InterruptPayload = {
  interrupt_id: "i1",
  kind: "choice",
  question: "Quel angle pour le second tour ?",
  options: [
    { label: "Plus concret", value: "concret" },
    { label: "Plus court", value: "court" },
  ],
};

/** État de la session côté serveur, lu par `GET` et renvoyé par les actions. */
const backend = {
  status: "running",
  lastSeq: 0,
  pending: null as InterruptPayload | null,
  tick: 0,
};
const view = () => {
  backend.tick += 1; // chaque écriture du serveur avance `updated_at`
  return {
    id: "s1",
    graph: "demo_debate",
    status: backend.status,
    last_seq: backend.lastSeq,
    pending_interrupt: backend.pending,
    error: null,
    tokens_in: 0,
    tokens_out: 0,
    cost_usd: 0,
    created_at: "2026-11-11T10:00:00Z",
    updated_at: `2026-11-11T10:00:${String(backend.tick).padStart(2, "0")}.000000Z`,
  };
};

function mount() {
  const fake = createFakeSocketServer();
  const router = createMemoryRouter(
    [{ path: "/demo", element: <DemoDebatePage createSocket={fake.factory} /> }],
    { initialEntries: ["/demo?session=s1"] },
  );
  const page = render(<RouterProvider router={router} />, { wrapper: createQueryWrapper() });
  return { fake, page, user: userEvent.setup() };
}

/** Publie côté « serveur » : le flux reçoit l'événement, `last_seq` avance. */
function publish(fake: ReturnType<typeof createFakeSocketServer>, ...events: SessionEvent[]) {
  for (const event of events) backend.lastSeq = Math.max(backend.lastSeq, event.seq);
  fake.last().push(...events);
}

/** Le statut affiché par la barre d'état finit par valoir `label`. */
const expectStatus = (label: string) =>
  waitFor(() =>
    expect(
      within(screen.getByRole("region", { name: "État de la session" })).getByText(label),
    ).toBeInTheDocument(),
  );

describe("DemoDebatePage : cycle de vie complet", () => {
  const history: SessionEvent[] = [];
  beforeEach(() => {
    useSessionStore.getState().reset("s1");
    Object.assign(backend, { status: "running", lastSeq: 0, pending: null, tick: 0 });
    history.length = 0;
    server.use(
      http.get(`${API}/s1`, () => HttpResponse.json(view())),
      http.post(`${API}/s1/message`, async ({ request }) => {
        const { text } = (await request.json()) as { text: string };
        history.push(userMsg(backend.lastSeq + 1, text)); // publié par le flux, pas ingéré ici
        return HttpResponse.json(history.at(-1), { status: 201 });
      }),
      http.post(`${API}/s1/resume`, () => {
        Object.assign(backend, { status: "running", pending: null });
        return HttpResponse.json(view(), { status: 202 });
      }),
      http.post(`${API}/s1/pause`, () => {
        Object.assign(backend, { status: "paused", pending: null });
        return HttpResponse.json(view());
      }),
    );
  });
  afterEach(() => useSessionStore.getState().reset("s1"));

  it("question, remarque, pause, rechargement, reprise après un tour coupé, fin", async () => {
    let { fake, page, user } = mount();
    await waitFor(() => expect(fake.sockets).toHaveLength(1));
    fake.last().open();
    const round1 = [
      started(1, "demo_proponent"),
      tok(2, "p1", "Pour", "demo_proponent"),
      message(3, "p1", "Pour.", "demo_proponent"),
      { ...interrupt(4, "i1"), payload: angle },
    ];
    Object.assign(backend, { status: "waiting_user", pending: angle });
    publish(fake, ...round1);
    history.push(...round1);
    const concret = await screen.findByRole("button", { name: "Plus concret" });
    expect(concret).toBeEnabled();

    // 1. Une remarque pendant la question : la carte reste active, le statut aussi (I1).
    await user.type(screen.getByLabelText("Ton message"), "Pense aux débutants{Enter}");
    await waitFor(() => expect(history.at(-1)?.type).toBe("user.message"));
    publish(fake, history.at(-1) as SessionEvent);
    expect(await screen.findByText("Pense aux débutants")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Plus concret" })).toBeEnabled();
    await expectStatus("En attente de ta réponse");

    // 2. Réponse, le Critique commence à écrire, puis pause.
    await user.click(screen.getByRole("button", { name: "Plus concret" }));
    expect(await screen.findByText("Réponse envoyée")).toBeInTheDocument();
    const round2 = [started(6, "demo_critic"), tok(7, "c1", "Moitié")];
    publish(fake, ...round2);
    history.push(...round2);
    await user.click(await screen.findByRole("button", { name: "Pause" }));
    await expectStatus("En pause");

    // 3. Rechargement : store vide, rejeu complet ; le statut vient du serveur (I2).
    page.unmount();
    useSessionStore.getState().reset("s1");
    ({ fake, page, user } = mount());
    await waitFor(() => expect(fake.sockets).toHaveLength(1));
    fake
      .last()
      .open()
      .push(...history);
    await expectStatus("En pause");
    expect(screen.queryByRole("button", { name: "Pause" })).not.toBeInTheDocument();
    // La question répondue reste repliée après le rechargement : plus d'option à cliquer.
    expect(screen.queryByRole("button", { name: "Plus concret" })).not.toBeInTheDocument();
    expect(screen.getByText("Réponse envoyée")).toBeInTheDocument();

    // 4. Reprise : le Critique rejoue son tour coupé (nouvel id), une seule bulle (I5).
    await user.click(screen.getByRole("button", { name: "Reprendre" }));
    await expectStatus("En cours");
    publish(
      fake,
      started(8, "demo_critic"),
      tok(9, "c2", "Entier"),
      message(10, "c2", "Entier."),
      completed(11),
    );
    expect(await screen.findByText("Entier.")).toBeInTheDocument();
    expect(screen.queryByText("Moitié")).not.toBeInTheDocument();
    expect(screen.getAllByRole("article", { name: "Critique" })).toHaveLength(1);
    await expectStatus("Terminée");
    expect(screen.getByRole("button", { name: "Nouveau débat" })).toBeInTheDocument();
  });
});
