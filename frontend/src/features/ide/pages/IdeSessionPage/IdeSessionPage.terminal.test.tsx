import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { expect, it } from "vitest";
import { API } from "@/test/councilApi";
import { progress } from "@/test/ideApi";
import { renderSession } from "../../ideTestkit";

it("affiche la sortie du terminal et transmet l’entrée et l’interruption", async () => {
  const actions: unknown[] = [];
  let killed = false;
  const { user } = renderSession({
    override: [
      http.post(`${API}/ide/sessions/s1/terminal`, () =>
        HttpResponse.json({ id: "t1" }, { status: 202 }),
      ),
      http.get(`${API}/ide/terminals/t1`, ({ request }) => {
        const after = new URL(request.url).searchParams.get("after");
        return HttpResponse.json(
          progress({
            id: "t1",
            status: killed ? "killed" : "running",
            output: after === "0" ? "Bac prêt\n" : "",
            next_offset: 10,
          }),
        );
      }),
      http.post(`${API}/ide/terminals/t1/input`, async ({ request }) => {
        actions.push(await request.json());
        return new HttpResponse(null, { status: 204 });
      }),
      http.delete(`${API}/ide/terminals/t1`, () => {
        actions.push("interrompu");
        killed = true;
        return new HttpResponse(null, { status: 204 });
      }),
    ],
  });

  await user.click(await screen.findByRole("button", { name: "Open terminal" }));
  await waitFor(() =>
    expect(screen.getByRole("log", { name: "Terminal output" })).toHaveTextContent("Bac prêt"),
  );
  await user.type(screen.getByRole("textbox", { name: "Terminal input" }), "afficher{Enter}");
  await user.click(screen.getByRole("button", { name: "Interrupt terminal" }));
  await waitFor(() => expect(actions).toEqual([{ data: "afficher\n" }, "interrompu"]));
});
