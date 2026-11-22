import { expect, test, type APIRequestContext } from "@playwright/test";
import { API, finishFirstLaunch } from "./support/firstLaunch.ts";

const service = new URL(API).origin;
const chat = "55001424";

type Challenge = { id: string; question: string };
type Claim = { challenge: Challenge | null };
type Rating = { step: number; due_date: string };

class FakeNod {
  readonly deliveries = new Map<string, string>();
  private readonly request: APIRequestContext;
  private readonly token: string;

  constructor(request: APIRequestContext, token: string) {
    this.request = request;
    this.token = token;
  }

  async tool<T>(name: string, args: Record<string, string> = {}): Promise<T> {
    const response = await this.request.post(`${service}/mcp`, {
      headers: { Authorization: `Bearer ${this.token}` },
      data: {
        jsonrpc: "2.0",
        id: 1,
        method: "tools/call",
        params: { name, arguments: { chat_id: chat, ...args } },
      },
    });
    expect(response.ok()).toBe(true);
    const reply = await response.json();
    expect(reply.result.isError).toBe(false);
    return (JSON.parse(reply.result.content[0].text) as { data: T }).data;
  }

  async poll() {
    const { challenge } = await this.tool<Claim>("message_review_claim");
    if (challenge && !this.deliveries.has(challenge.id)) {
      this.deliveries.set(challenge.id, challenge.question);
    }
  }
}

test("autorise Nod, reçoit une seule question et enregistre l’avis Telegram", async ({
  page,
  request,
}) => {
  await finishFirstLaunch(request);
  expect((await request.post(`${service}/e2e/message-review/card`)).ok()).toBe(true);
  expect((await request.put(`${API}/mcp/settings`, { data: { enabled: true } })).ok()).toBe(true);
  const created = await request.post(`${API}/mcp/tokens`, {
    data: { label: "Nod recette", features: ["message_review"], mode: "write" },
  });
  expect(created.status()).toBe(201);
  const connection = (await created.json()) as { id: string; token: string };

  await page.goto("/reglages/revision-messagerie");
  await expect(page.getByRole("heading", { name: "Révision par messagerie" })).toBeVisible();
  const optIn = page.getByRole("checkbox", { name: "Autoriser les questions de Nod" });
  await expect(optIn).not.toBeChecked();
  await optIn.press("Space");
  await page.getByText("Créneau dans le fuseau du compte (Europe/Paris).").waitFor();
  await page.getByLabel("Jeton de Nod").selectOption(connection.id);
  await page.getByLabel("Identifiant de discussion privée").fill(chat);
  const save = page.getByRole("button", { name: "Enregistrer" });
  await save.press("Enter");
  await expect(page.getByRole("status").filter({ hasText: "Réglages enregistrés." })).toBeVisible();
  await expect(save).toBeFocused();

  const nod = new FakeNod(request, connection.token);
  await nod.poll();
  await nod.poll();
  const [delivery] = [...nod.deliveries];
  expect(nod.deliveries.size).toBe(1);
  expect(delivery?.[1]).toContain("À quoi sert un index ?");
  const challenge_id = delivery?.[0] ?? "";
  const flipped = await nod.tool<{ answer: string }>("message_review_reveal", { challenge_id });
  expect(flipped.answer).toContain("Il repère des valeurs.");
  const first = await nod.tool<Rating>("message_review_answer", { challenge_id, result: "ok" });
  const replay = await nod.tool<Rating>("message_review_answer", { challenge_id, result: "ok" });
  expect(first).toEqual(replay);
  expect(first.step).toBe(2);
  const queue = await request.get(`${API}/flashcards/due`);
  expect(await queue.json()).toMatchObject({ cards: [], reviewed_today: 1 });
  await page.reload();
  await expect(optIn).toBeChecked();
});
