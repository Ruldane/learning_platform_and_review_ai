import { applicationOut } from "@/test/applicationsApi";
import { renderApplications } from "@/test/applicationsHarness";
import { committeeApi, type CommitteeApiOptions } from "@/test/committeeApi";
import { createFakeSocketServer } from "@/test/fakeSocket";
import { server } from "@/test/server";
import { applicationsManifest } from "../../manifest";
import { CommitteePage } from "./CommitteePage";

const ROUTE = "candidatures/:applicationId/comite";

/** La session d'un comité lancé depuis la page (celle que `committeeApi` range au lancement). */
export const SESSION = "cm-s-new";

/** Monte la page du comité de la fiche `a1` (offre `p1`, version `v1`) avec les routes en mémoire. */
export function setup(
  options: CommitteeApiOptions = {},
  application: Record<string, unknown> = {},
  path = "/candidatures/a1/comite",
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
