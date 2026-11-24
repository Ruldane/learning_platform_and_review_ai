import { screen } from "@testing-library/react";
import { applicationOut } from "@/test/applicationsApi";
import { openStream, renderApplications } from "@/test/applicationsHarness";
import { councilEvents } from "@/test/councilEvents";
import { createFakeSocketServer } from "@/test/fakeSocket";
import { interviewApi, type InterviewApiOptions } from "@/test/interviewApi";
import { server } from "@/test/server";
import { applicationsManifest } from "../../manifest";
import { InterviewPage } from "./InterviewPage";

const ROUTE = "candidatures/:applicationId/entretien";
export const SESSION = "iv-s-new";

export function setup(options: InterviewApiOptions = {}, path = "/candidatures/a1/entretien") {
  const sockets = createFakeSocketServer();
  const interviews = interviewApi(options);
  server.use(...interviews.handlers);
  const routes = applicationsManifest.routes.map((route) =>
    route.path === ROUTE
      ? { path: route.path, element: <InterviewPage createSocket={sockets.factory} /> }
      : route,
  );
  const view = renderApplications(routes, path, {
    applications: [applicationOut({ id: "a1", company: "Acme", title: "Data engineer" })],
  });
  return { ...view, sockets, interviews };
}

/** Start an interview with the default settings and open its session stream. */
export async function startInterview(view: ReturnType<typeof setup>) {
  await view.user.click(await screen.findByRole("button", { name: "Start the interview" }));
  const stream = await openStream(view.sockets, SESSION);
  return { stream, e: councilEvents(SESSION) };
}

export const ask = (
  e: ReturnType<typeof councilEvents>,
  n: number,
  interruptId: string,
  text: string,
) => [
  e.message(`interviewer-q${n}`, text, "interviewer"),
  e.interrupt("interview_answer", interruptId, {
    question: text,
    options: [{ value: "stop", label: "End the interview" }],
    fields: [{ id: "answer", label: "Your answer", required: true, max_length: 4000 }],
  }),
];
