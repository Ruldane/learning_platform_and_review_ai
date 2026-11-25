import { applicationOut } from "@/test/applicationsApi";
import { renderApplications } from "@/test/applicationsHarness";
import { committeeApi, type CommitteeApiOptions } from "@/test/committeeApi";
import { createFakeSocketServer } from "@/test/fakeSocket";
import { server } from "@/test/server";
import { applicationsManifest } from "../../manifest";
import { CommitteePage } from "./CommitteePage";

const ROUTE = "applications/:applicationId/committee";

/** The session of a committee started from the page (the one `committeeApi` stores at start). */
export const SESSION = "cm-s-new";

/** Mounts the committee page of record `a1` (posting `p1`, version `v1`) with in-memory routes. */
export function setup(
  options: CommitteeApiOptions = {},
  application: Record<string, unknown> = {},
  path = "/applications/a1/committee",
) {
  const sockets = createFakeSocketServer();
  const committee = committeeApi(options);
  server.use(...committee.handlers);
  const routes = applicationsManifest.routes.map((route) =>
    route.path === ROUTE
      ? { path: route.path, element: <CommitteePage createSocket={sockets.factory} /> }
      : route,
  );
  const view = renderApplications(routes, path, {
    applications: [
      applicationOut({
        id: "a1",
        company: "Acme",
        title: "Data engineer",
        posting_id: "p1",
        cv_version_id: "v1",
        ...application,
      }),
    ],
  });
  return { ...view, sockets, committee };
}
