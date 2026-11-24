import { screen } from "@testing-library/react";
import { expect } from "vitest";
import { councilEvents } from "./councilEvents";
import { openStream } from "./cvHarness";
import type { FakeSocketServer } from "./fakeSocket";

export const OUTPUT_OPTIONS = [
  { value: "report", label: "View the report" },
  { value: "pdf", label: "Generate PDF" },
  { value: "finish", label: "Finish" },
];

/** La question de sortie de la revue, rejouée dans le flux `r1` (comme après un rechargement). */
export async function askOutput(sockets: FakeSocketServer) {
  const stream = await openStream(sockets, "r1");
  const e = councilEvents("r1");
  stream.push(
    e.message("m1", "Suggested changes are ready.", "recruiter"),
    e.interrupt("cv_output", "o1", {
      question: "What would you like to do next?",
      options: OUTPUT_OPTIONS,
    }),
  );
  expect(await screen.findByRole("button", { name: "Generate PDF" })).toBeInTheDocument();
  return stream;
}
