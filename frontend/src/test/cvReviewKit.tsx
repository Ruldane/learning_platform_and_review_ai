import { screen } from "@testing-library/react";
import { expect } from "vitest";
import { councilEvents } from "./councilEvents";
import { openStream } from "./cvHarness";
import type { FakeSocketServer } from "./fakeSocket";

export const OUTPUT_OPTIONS = [
  { value: "report", label: "Voir le rapport" },
  { value: "pdf", label: "Générer le PDF" },
  { value: "finish", label: "Terminer" },
];

/** La question de sortie de la revue, rejouée dans le flux `r1` (comme après un rechargement). */
export async function askOutput(sockets: FakeSocketServer) {
  const stream = await openStream(sockets, "r1");
  const e = councilEvents("r1");
  stream.push(
    e.message("m1", "N modifications proposées.", "recruiter"),
    e.interrupt("cv_output", "o1", {
      question: "Que veux-tu faire du CV ciblé ?",
      options: OUTPUT_OPTIONS,
    }),
  );
  expect(await screen.findByRole("button", { name: "Générer le PDF" })).toBeInTheDocument();
  return stream;
}
