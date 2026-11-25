import { screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { ReviewPage } from "./ReviewPage";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { modificationOut, refusal, reviewOut, versionOut } from "@/test/cvApi";
import { renderCv } from "@/test/cvHarness";

function renderReview(api: Parameters<typeof renderCv>[3] = {}) {
  return renderCv(
    "/career/cv/reviews/:reviewId",
    "/career/cv/reviews/rv1",
    (createSocket) => <ReviewPage pollMs={40} createSocket={createSocket} />,
    api,
  );
}

describe("ReviewPage: editing and placing modifications", () => {
  beforeEach(() => useSessionStore.getState().reset("r1"));

  it("sends an edited « à confirmer » text without the confirmation", async () => {
    const { user, state } = renderReview();
    const toConfirm = (await screen.findAllByRole("article"))[1]!;
    await user.click(within(toConfirm).getByRole("button", { name: "Edit" }));
    const field = within(toConfirm).getByLabelText("Edited text");
    await user.clear(field);
    await user.type(field, "Déploiement sur Kubernetes pendant 2 ans");
    await user.click(within(toConfirm).getByRole("button", { name: "Save and accept" }));
    await waitFor(() => expect(state.patches).toHaveLength(1));
    expect(state.patches[0]).toEqual({
      id: "m2",
      body: {
        status: "accepted",
        after: "Déploiement sur Kubernetes pendant 2 ans",
        confirm: false,
      },
    });
  });

  it("keeps the editor open with the typed text and shows the refusal", async () => {
    const { user } = renderReview({
      patchModification: () =>
        refusal(422, "keyword_not_in_profile", "Le mot clé « AWS » n'est pas dans ton profil."),
    });
    const first = (await screen.findAllByRole("article"))[0]!;
    await user.click(within(first).getByRole("button", { name: "Edit" }));
    const field = within(first).getByLabelText("Edited text");
    await user.clear(field);
    await user.type(field, "Pipelines de 2 To sur AWS");
    await user.click(within(first).getByRole("button", { name: "Save and accept" }));
    expect(await within(first).findByRole("alert")).toHaveTextContent(
      "Le mot clé « AWS » n'est pas dans ton profil.",
    );
    expect(within(first).getByLabelText("Edited text")).toHaveValue("Pipelines de 2 To sur AWS");
  });

  it("offers no « Modifier » on a removal or a move", async () => {
    renderReview({
      reviews: [
        reviewOut({
          modifications: [
            modificationOut("m1", { action: "remove", after: "" }),
            modificationOut("m2", { action: "move", ref: "r2" }),
          ],
        }),
      ],
    });
    expect(await screen.findAllByRole("article")).toHaveLength(2);
    expect(screen.queryByRole("button", { name: "Edit" })).toBeNull();
  });

  it("says which accepted modification the generated CV could not place", async () => {
    renderReview({
      reviews: [
        reviewOut({
          modifications: [
            modificationOut("m1", { status: "accepted", ref: "a1" }),
            modificationOut("m2", { status: "accepted", ref: "a2" }),
          ],
          versions: [versionOut({ decisions: { a1: "ignored", a2: "accepted" } })],
          waiting_output: false,
          status: "done",
        }),
      ],
    });
    const [first, second] = await screen.findAllByRole("article");
    expect(within(first!).getByText("Not placed in version 1")).toBeInTheDocument();
    expect(within(second!).queryByText(/Not placed/)).toBeNull();
    expect(
      await screen.findByText("1 accepted change couldn't be placed in this CV."),
    ).toBeInTheDocument();
  });
});
