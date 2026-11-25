import { screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { noteOut } from "@/test/ideApi";
import { findEditor, renderSession } from "../../ideTestkit";

it("ouvre le fichier du projet lié à une note du professeur", async () => {
  const { user } = renderSession({
    session: { files: { "main.py": "a = 1", "src/calcul.py": "x = 2" } },
    notes: [noteOut({ file_path: "src/calcul.py", line_start: 1 })],
  });
  expect(await findEditor()).toHaveValue("a = 1");
  await user.click(await screen.findByRole("button", { name: "Open src/calcul.py" }));
  expect(await findEditor()).toHaveValue("x = 2");
});
