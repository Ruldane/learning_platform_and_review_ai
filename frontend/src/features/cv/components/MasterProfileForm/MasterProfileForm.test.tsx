import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { MasterProfileView, ProfileSaveErrorView } from "../viewTypes";
import { MasterProfileForm } from "./MasterProfileForm";

const PROFILE: MasterProfileView = {
  identity: {
    name: "Camille Exemple",
    email: "camille.exemple@example.org",
    phone: "+33 6 00 00 00 00",
    location: "Lyon",
    headline: null,
  },
  title: { id: "t1", text: "Développeuse front" },
  summary: null,
  experiences: [
    {
      id: "x1",
      role: "Développeuse",
      company: "Société Fictive",
      location: null,
      start: "2021-03",
      end: null,
      achievements: [{ id: "x1a1", text: "Refonte du tableau de bord" }],
      sources: ["cv", "linkedin"],
    },
  ],
  education: [],
  skills: [
    { id: "c1", name: "React", category: "Front", sources: ["cv"] },
    { id: "c2", name: "SQL", category: null, sources: ["note"] },
    { id: "c3", name: "Git", category: null, sources: ["cv"] },
  ],
  projects: [],
  languages: [{ id: "l1", name: "Français", level: "Natif", sources: ["cv"] }],
  links: [],
};

interface Props {
  profile?: MasterProfileView;
  dropped?: string[];
  saving?: boolean;
  error?: ProfileSaveErrorView | null;
}

function setup(props: Props = {}) {
  const onSave = vi.fn();
  const ui = (next: Props) => (
    <MasterProfileForm
      profile={next.profile ?? PROFILE}
      dropped={next.dropped ?? []}
      saving={next.saving ?? false}
      error={next.error ?? null}
      onSave={onSave}
    />
  );
  const view = render(ui(props));
  return { onSave, rerender: (next: Props) => view.rerender(ui(next)) };
}

const open = (name: string) => userEvent.click(screen.getByRole("button", { name }));
const save = () => userEvent.click(screen.getByRole("button", { name: "Enregistrer le profil" }));
const saved = (onSave: ReturnType<typeof vi.fn>): MasterProfileView =>
  onSave.mock.calls[0]?.[0] as MasterProfileView;

describe("MasterProfileForm", () => {
  it("has the nine collapsible sections, only the identity open", () => {
    setup();
    const titles = [
      "Identité",
      "Titre",
      "Résumé",
      "Expériences (1)",
      "Formation (0)",
      "Compétences (3)",
      "Projets (0)",
      "Langues (1)",
      "Liens (0)",
    ];
    for (const title of titles) {
      const expanded = title === "Identité";
      expect(screen.getByRole("button", { name: title })).toHaveAttribute(
        "aria-expanded",
        String(expanded),
      );
    }
    expect(screen.getByRole("textbox", { name: "Nom" })).toHaveValue("Camille Exemple");
    expect(screen.queryByRole("textbox", { name: /Poste/ })).not.toBeInTheDocument();
  });

  it("opens and closes a section", async () => {
    setup();
    await open("Expériences (1)");
    expect(screen.getByRole("textbox", { name: "Poste (Expérience 1)" })).toHaveValue(
      "Développeuse",
    );
    await open("Expériences (1)");
    expect(screen.queryByRole("textbox", { name: /Poste/ })).not.toBeInTheDocument();
  });

  it("shows the sources of each fact as badges", async () => {
    setup();
    await open("Expériences (1)");
    await open("Compétences (3)");
    const row = screen.getByRole("group", { name: /Expérience 1/ });
    expect(
      within(row)
        .getAllByRole("listitem")
        .map((item) => item.textContent)
        .filter((text) => text === "CV" || text === "LinkedIn"),
    ).toEqual(["CV", "LinkedIn"]);
    expect(screen.getByRole("group", { name: /Compétence 2/ })).toHaveTextContent("Note");
  });

  it("adds an achievement and returns the whole profile", async () => {
    const { onSave } = setup();
    await open("Expériences (1)");
    await userEvent.click(
      screen.getByRole("button", { name: "Ajouter une réalisation à l'expérience 1" }),
    );
    await userEvent.type(
      screen.getByRole("textbox", { name: "Réalisation 2 (Expérience 1)" }),
      "Mise en place des tests",
    );
    await save();
    const profile = saved(onSave);
    expect(profile.experiences[0]?.achievements).toEqual([
      { id: "x1a1", text: "Refonte du tableau de bord" },
      { id: "", text: "Mise en place des tests" },
    ]);
    expect(profile).toEqual({
      ...PROFILE,
      experiences: [
        { ...PROFILE.experiences[0], achievements: profile.experiences[0]?.achievements },
      ],
    });
  });

  it("removes a skill", async () => {
    const { onSave } = setup();
    await open("Compétences (3)");
    await userEvent.click(screen.getByRole("button", { name: "Retirer la compétence 2" }));
    expect(screen.getByRole("button", { name: "Compétences (2)" })).toBeInTheDocument();
    await save();
    expect(saved(onSave).skills.map((skill) => skill.name)).toEqual(["React", "Git"]);
  });

  it("adds an experience tagged with the source Toi and without id", async () => {
    const { onSave } = setup();
    await open("Expériences (1)");
    await userEvent.click(screen.getByRole("button", { name: "Ajouter une expérience" }));
    expect(screen.getByRole("group", { name: /Expérience 2/ })).toHaveTextContent("Toi");
    await userEvent.type(
      screen.getByRole("textbox", { name: "Poste (Expérience 2)" }),
      "Stagiaire",
    );
    await userEvent.type(
      screen.getByRole("textbox", { name: "Entreprise (Expérience 2)" }),
      "Acme",
    );
    await save();
    expect(saved(onSave).experiences[1]).toMatchObject({
      id: "",
      role: "Stagiaire",
      company: "Acme",
      location: null,
      sources: ["january"],
    });
  });

  it("sends a blank optional field as null and drops a blank line", async () => {
    const { onSave } = setup();
    await userEvent.clear(screen.getByRole("textbox", { name: "Lieu" }));
    await open("Expériences (1)");
    await userEvent.click(
      screen.getByRole("button", { name: "Ajouter une réalisation à l'expérience 1" }),
    );
    await save();
    const profile = saved(onSave);
    expect(profile.identity.location).toBeNull();
    expect(profile.experiences[0]?.achievements).toHaveLength(1);
  });

  it("puts a server error under its field, found by its path", () => {
    setup({
      error: {
        message: "Certains champs sont à corriger.",
        fields: { "experiences.0.role": "Ce champ est obligatoire." },
      },
    });
    // La section de l'erreur s'ouvre d'elle-même.
    const role = screen.getByRole("textbox", { name: "Poste (Expérience 1)" });
    expect(role).toHaveAttribute("aria-invalid", "true");
    expect(role).toHaveAccessibleDescription("Ce champ est obligatoire.");
    expect(screen.getByRole("textbox", { name: "Entreprise (Expérience 1)" })).not.toHaveAttribute(
      "aria-invalid",
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Certains champs sont à corriger.");
    expect(screen.getByRole("button", { name: "Compétences (3)" })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
  });

  it("places an error on a line of a nested list", async () => {
    setup({
      error: {
        message: "À corriger.",
        fields: { "experiences.0.achievements.0.text": "Trop long." },
      },
    });
    expect(
      screen.getByRole("textbox", { name: "Réalisation 1 (Expérience 1)" }),
    ).toHaveAccessibleDescription("Trop long.");
  });

  it("announces the dropped lines", () => {
    const { rerender } = setup({ dropped: ["Augmenté les ventes de 400 %"] });
    expect(
      screen.getByText("1 ligne retirée : chiffre introuvable dans tes documents."),
    ).toBeInTheDocument();
    expect(screen.getByText("Augmenté les ventes de 400 %")).toBeInTheDocument();
    rerender({ dropped: ["a", "b"] });
    expect(
      screen.getByText("2 lignes retirées : chiffres introuvables dans tes documents."),
    ).toBeInTheDocument();
  });

  it("shows no banner without dropped line", () => {
    setup();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("locks everything while saving", () => {
    setup({ saving: true });
    expect(screen.getByRole("button", { name: "Enregistrement…" })).toBeDisabled();
    expect(screen.getByRole("textbox", { name: "Nom" })).toBeDisabled();
  });

  it("starts over from a new profile", () => {
    const { rerender } = setup();
    rerender({ profile: { ...PROFILE, identity: { ...PROFILE.identity, name: "Autre Nom" } } });
    expect(screen.getByRole("textbox", { name: "Nom" })).toHaveValue("Autre Nom");
  });

  it("can be used with the keyboard only", async () => {
    const { onSave } = setup();
    const skills = screen.getByRole("button", { name: "Compétences (3)" });
    skills.focus();
    await userEvent.keyboard("{Enter}");
    expect(skills).toHaveAttribute("aria-expanded", "true");
    await userEvent.tab();
    expect(screen.getByRole("textbox", { name: "Compétence (Compétence 1)" })).toHaveFocus();
    await userEvent.keyboard("{End} 2");
    screen.getByRole("button", { name: "Enregistrer le profil" }).focus();
    await userEvent.keyboard("{Enter}");
    expect(saved(onSave).skills[0]?.name).toBe("React 2");
  });
});
