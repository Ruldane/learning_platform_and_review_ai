import { expect, test, type APIRequestContext } from "@playwright/test";
import { API, finishFirstLaunch } from "./support/firstLaunch.ts";

const service = new URL(API).origin;
const chat = "55001424";
type Invitation = { id: string; day: string };
type Question = { id: string; text: string };
type State = {
  status: string;
  question: Question | null;
  debrief: { scores: { clarte: number } } | null;
};

async function createToken(request: APIRequestContext, feature: string) {
  const response = await request.post(`${API}/mcp/tokens`, {
    data: { label: feature, features: [feature], mode: "write" },
  });
  expect(response.status()).toBe(201);
  return (await response.json()) as { id: string; token: string };
}

function fakeNod(request: APIRequestContext, token: string) {
  return async function tool<T>(action: string, input: Record<string, string> = {}): Promise<T> {
    const response = await request.post(`${service}/mcp`, {
      headers: { Authorization: `Bearer ${token}` },
      data: {
        jsonrpc: "2.0",
        id: 1,
        method: "tools/call",
        params: { name: `surprise_interview_${action}`, arguments: { chat_id: chat, ...input } },
      },
    });
    expect(response.ok()).toBe(true);
    const reply = await response.json();
    expect(reply.result.isError).toBe(false);
    return (JSON.parse(reply.result.content[0].text) as { data: T }).data;
  };
}

test("accepte une invitation Nod et reçoit un bilan après trois questions techniques", async ({
  page,
  request,
}) => {
  await finishFirstLaunch(request);
  expect((await request.put(`${API}/mcp/settings`, { data: { enabled: true } })).ok()).toBe(true);
  const revision = await createToken(request, "message_review");
  const transport = await createToken(request, "surprise_interview");
  const linked = await request.put(`${API}/message-reviews/settings`, {
    data: { enabled: true, token_id: revision.id, chat_id: chat, start: "18:00", end: "19:00" },
  });
  expect(linked.ok()).toBe(true);
  await page.goto("/reglages/entretien-surprise");
  await expect(page.getByRole("heading", { name: "Entretien surprise" })).toBeVisible();
  await expect(page.getByText("Créneau de 18:00 à 19:00 · Europe/Paris")).toBeVisible();
  const consent = page.getByRole("checkbox", { name: "Autoriser les invitations d’entretien" });
  await expect(consent).not.toBeChecked();
  await consent.press("Space");
  await page.getByLabel("Poste à préparer").fill("Ingénieure Python");
  await page.getByLabel("Jeton Nod pour l’entretien").selectOption(transport.id);
  const save = page.getByRole("button", { name: "Enregistrer" });
  await save.press("Enter");
  await expect(page.getByRole("status").filter({ hasText: "Réglages enregistrés." })).toBeVisible();
  await expect(save).toBeFocused();
  expect((await request.post(`${service}/e2e/surprise-interview/ready`)).ok()).toBe(true);

  const tool = fakeNod(request, transport.token);
  const invite = await tool<{ invitation: Invitation }>("invite");
  expect(await tool("invite")).toEqual(invite);
  expect(await (await request.get(`${API}/interviews`)).json()).toEqual([]);
  const params = { invitation_id: invite.invitation.id };
  const started = await tool<{ interview_id: string; session_id: string }>("accept", params);
  expect(await tool("accept", params)).toEqual(started);
  for (let rank = 1; rank <= 3; rank++) {
    await expect
      .poll(async () => (await tool<State>("state", params)).question?.text, {
        timeout: 12000,
      })
      .toContain(`Question numéro ${rank}`);
    const current = await tool<State>("state", params);
    expect(await tool("state", params)).toEqual(current);
    const reply = {
      ...params,
      question_id: current.question?.id ?? "",
      message_id: String(rank),
      answer: `Une réponse technique détaillée à la question ${rank}.`,
    };
    expect(await tool("answer", reply)).toEqual({ received: true });
    expect(await tool("answer", reply)).toEqual({ received: true });
  }
  await expect.poll(async () => (await tool<State>("state", params)).status).toBe("done");
  expect((await tool<State>("state", params)).debrief?.scores.clarte).toBe(4);
  const saved = await (await request.get(`${API}/interviews/${started.interview_id}`)).json();
  expect(saved.exchanges).toHaveLength(3);
  expect(
    saved.exchanges.map((exchange: { follow_up: string | null }) => exchange.follow_up),
  ).toEqual([null, null, null]);
  await page.reload();
  await expect(consent).toBeChecked();
});
