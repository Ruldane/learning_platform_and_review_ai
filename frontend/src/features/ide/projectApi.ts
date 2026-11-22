import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";

export type TabsState = components["schemas"]["ProjectTabsState"];
export type ProjectCommand =
  | { kind: "create"; path: string }
  | { kind: "rename"; path: string; destination: string }
  | { kind: "remove"; path: string; replacementEntry?: string };

const filesPath = "/ide/sessions/{session_id}/files";

export async function editProjectFile(sessionId: string, version: number, command: ProjectCommand) {
  const params = { path: { session_id: sessionId } };
  const body = { path: command.path, version };
  switch (command.kind) {
    case "create":
      return unwrap(await api.POST(filesPath, { params, body: { ...body, content: "" } }));
    case "rename":
      return unwrap(
        await api.PATCH(filesPath, { params, body: { ...body, destination: command.destination } }),
      );
    case "remove":
      return unwrap(
        await api.DELETE(filesPath, {
          params,
          body: { ...body, replacement_entry: command.replacementEntry },
        }),
      );
  }
}

export async function putProjectTabs(sessionId: string, body: TabsState) {
  const params = { path: { session_id: sessionId } };
  return unwrap(await api.PUT("/ide/sessions/{session_id}/tabs", { params, body }));
}
