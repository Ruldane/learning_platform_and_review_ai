import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { expect, it } from "vitest";
import { API } from "@/test/councilApi";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { OncallPage } from "./OncallPage";

const base = `${API}/oncall/incidents`;
const observed: string[] = [];
const exercise = {
  id: "incident-fictif",
  kind: "queue",
  title: "Processing queue",
  seed: 303,
  minute: 1,
  alerted: false,
  ide_session_id: "projet-fictif",
  observed_events: observed,
  events: [{ id: "1", minute: 1, kind: "sample", metric: "queue", value: 0 }],
  diagnostic: { state: "idle", run_id: null },
  review_state: "idle",
  proof_recorded: false,
};

it("déclenche l’alerte au pas virtuel et ouvre le journal et le projet de réparation", async () => {
  let current = exercise;
  const alert = { id: "2", minute: 2, kind: "alert", metric: "queue", value: 3 };
  server.use(
    http.get(base, () => HttpResponse.json([current])),
    http.get(`${base}/${exercise.id}`, () => HttpResponse.json(current)),
    http.post(`${base}/${exercise.id}/advance`, () => {
      const opened = { ...current, alerted: true, minute: 2, events: [alert] };
      current = opened;
      return HttpResponse.json(opened);
    }),
    http.post(`${base}/${exercise.id}/events/2/observe`, () => {
      current = { ...current, observed_events: ["2"] };
      return HttpResponse.json(current);
    }),
  );
  const routes = [{ path: "/on-call/:incidentId", element: <OncallPage /> }];
  const { user } = renderRoutes(routes, `/on-call/${exercise.id}`);

  expect(await screen.findByText("Waiting for an alert")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Advance one minute" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Simulated alert");
  expect(screen.getByRole("link", { name: "Open the Python project" })).toHaveAttribute(
    "href",
    "/code/projet-fictif",
  );
  const observation = screen.getByRole("button", { name: "View event 2" });
  await user.click(observation);
  expect(await screen.findByRole("button", { name: "Event 2 viewed" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
});
