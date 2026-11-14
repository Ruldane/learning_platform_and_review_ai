import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { API } from "@/test/councilApi";
import { councilEvents } from "@/test/councilEvents";
import { emptyProfile, profileOut, refusal } from "@/test/cvApi";
import { openStream, renderCv } from "@/test/cvHarness";
import { server } from "@/test/server";
import { ProfilePage } from "./ProfilePage";

const draftState = {
  draft: profileOut(),
  validated: null,
  session_id: null,
  source_document_id: null,
};
const capturing = { draft: null, validated: null, session_id: "s1", source_document_id: null };

function setup(api: Parameters<typeof renderCv>[3] = {}) {
  return renderCv(
    "/carriere/profil",
    "/carriere/profil",
    (createSocket) => <ProfilePage pollMs={40} createSocket={createSocket} />,
    api,
  );
}

const validate = () => screen.findByRole("button", { name: "Valider mon profil" });

describe("ProfilePage", () => {
  beforeEach(() => useSessionStore.getState().reset("s1"));

  it("asks for the documents when there is no profile, then follows the reading", async () => {
    const { user, sockets, state } = setup({ profiles: [emptyProfile, capturing] });
    const cv = await screen.findByLabelText(/Ton CV \(PDF\)/);
    await user.upload(cv, new File(["%PDF-1.4"], "cv.pdf", { type: "application/pdf" }));
    await user.click(screen.getByRole("button", { name: "Créer mon profil maître" }));
    const stream = await openStream(sockets, "s1");
    stream.push(councilEvents("s1").message("m1", "Je lis ton CV.", "archivist"));
    expect(await screen.findByText("Je lis ton CV.")).toBeInTheDocument();
    expect(state.imports).toHaveLength(1);
    expect(state.imports[0]).toMatch(/^multipart\/form-data; boundary=/);
  });

  it("shows the draft, then validates it with the version that was read", async () => {
    const { user, state } = setup({ profiles: [draftState] });
    expect(await screen.findByRole("heading", { name: "Brouillon à relire" })).toBeInTheDocument();
    await user.click(await validate());
    await waitFor(() => expect(state.puts).toHaveLength(1));
    const body = state.puts[0] as {
      base_version: number;
      data: { title: { id: string; sources: string[] }; summary: { sources: string[] } };
    };
    expect(body.base_version).toBe(2);
    // Le titre et le résumé gardent leurs sources.
    expect(body.data.title).toEqual({ id: "t1", text: "Ingénieure données", sources: ["cv"] });
    expect(body.data.summary.sources).toEqual(["cv", "linkedin"]);
    expect(await screen.findByText(/Profil validé : version 3/)).toBeInTheDocument();
  });

  it("says the profile changed on a 409 and reloads it on demand", async () => {
    const { user, state } = setup({
      profiles: [draftState],
      putProfile: () => refusal(409, "profile_conflict", "Conflit."),
    });
    await user.click(await validate());
    expect(
      await screen.findByText("Le profil a changé : recharge pour voir sa dernière version."),
    ).toBeInTheDocument();
    const reads = state.reads.profile;
    await user.click(screen.getByRole("button", { name: "Recharger le profil" }));
    await waitFor(() => expect(state.reads.profile).toBeGreaterThan(reads));
    expect(screen.queryByText(/Le profil a changé/)).not.toBeInTheDocument();
  });

  it("points at the fields a 422 names, without any value", async () => {
    const { user } = setup({
      profiles: [draftState],
      putProfile: () =>
        refusal(422, "validation_error", "Certains champs sont invalides.", {
          fields: ["identity.name"],
        }),
    });
    await user.click(await validate());
    expect(await screen.findByText("Certains champs sont à corriger.")).toBeInTheDocument();
    expect(screen.getAllByText("Ce champ est à corriger.").length).toBeGreaterThan(0);
  });

  it("edits a validated profile and lists its versions", async () => {
    const { user, state } = setup({
      profiles: [
        {
          draft: null,
          validated: profileOut({ version: 4, status: "validated" }),
          session_id: null,
          source_document_id: null,
        },
      ],
      profileVersions: [
        { version: 4, status: "validated", source: "january", created_at: "2026-11-12T10:00:00Z" },
        { version: 3, status: "validated", source: "january", created_at: "2026-11-11T10:00:00Z" },
      ],
    });
    expect(
      await screen.findByRole("heading", { name: "Profil validé : version 4" }),
    ).toBeInTheDocument();
    const list = await screen.findByRole("list", { name: "Versions du profil maître" });
    expect(within(list).getAllByRole("listitem")).toHaveLength(2);
    await user.click(await validate());
    await waitFor(() => expect(state.puts).toHaveLength(1));
    expect((state.puts[0] as { base_version: number }).base_version).toBe(4);
  });

  it("offers to start the import again when the reading stops", async () => {
    const { sockets, user, state } = setup({ profiles: [capturing] });
    const stream = await openStream(sockets, "s1");
    stream.push(councilEvents("s1").failed("Le modèle ne répond pas."));
    expect(await screen.findByText("Le modèle ne répond pas.")).toBeInTheDocument();
    const reads = state.reads.profile;
    await user.click(screen.getByRole("button", { name: "Recommencer l'import" }));
    await waitFor(() => expect(state.reads.profile).toBeGreaterThan(reads));
  });

  it("shows a loading state, then an error with « Réessayer »", async () => {
    const { user } = setup({ profile: () => HttpResponse.json({}, { status: 500 }) });
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    server.use(http.get(`${API}/profile`, () => HttpResponse.json(draftState)));
    await user.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(await screen.findByRole("heading", { name: "Brouillon à relire" })).toBeInTheDocument();
  });
});
