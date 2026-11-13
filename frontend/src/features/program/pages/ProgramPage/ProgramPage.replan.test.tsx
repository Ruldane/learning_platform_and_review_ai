import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { programApi, programOut, sessionOut } from "@/test/programApi";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { ProgramPage } from "./ProgramPage";

function setup(program: Record<string, unknown>, waiting: Record<string, unknown>[] = []) {
  const api = programApi({ program });
  api.state.waitingReplans = waiting;
  server.use(...api.handlers);
  return renderRoutes(
    [
      { path: "/apprendre/programme/:programId", element: <ProgramPage /> },
      {
        path: "/apprendre/programme/:programId/replanification",
        element: <h1>Replanification</h1>,
      },
    ],
    "/apprendre/programme/p1",
  );
}

const waitingReplan = (subjectId = "p1") =>
  sessionOut("s9", "waiting_user", {
    graph: "replan",
    subject_type: "program",
    subject_id: subjectId,
  });

describe("ProgramPage replan entry", () => {
  it("shows the replan banner on the program page", async () => {
    const { user, router } = setup(programOut({ status: "validated" }), [waitingReplan()]);
    expect(await screen.findByText("Une replanification attend ta réponse")).toBeInTheDocument();
    await user.click(screen.getByRole("link", { name: "Voir la proposition" }));
    expect(router.state.location.pathname).toBe("/apprendre/programme/p1/replanification");
  });

  it("ignores a waiting replan of another program", async () => {
    setup(programOut({ status: "validated" }), [waitingReplan("p2")]);
    await screen.findByRole("heading", { name: "Python pour la data", level: 1 });
    expect(screen.getByRole("link", { name: "Replanifier" })).toBeInTheDocument();
    expect(screen.queryByText("Une replanification attend ta réponse")).toBeNull();
  });

  it("offers « Replanifier » for a validated program only", async () => {
    const { user, router } = setup(programOut({ status: "validated" }));
    await user.click(await screen.findByRole("link", { name: "Replanifier" }));
    expect(router.state.location.pathname).toBe("/apprendre/programme/p1/replanification");
  });

  it("does not offer « Replanifier » on a draft", async () => {
    setup(programOut({ status: "draft" }));
    await screen.findByRole("heading", { name: "Python pour la data", level: 1 });
    expect(screen.queryByRole("link", { name: "Replanifier" })).toBeNull();
  });
});
