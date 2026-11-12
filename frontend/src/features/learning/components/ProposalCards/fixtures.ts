import type { ProposalView } from "../viewTypes";

/** Trois propositions pour les tests des cartes et de la page. */
export function makeProposals(): ProposalView[] {
  return [
    {
      id: "p1",
      rank: 1,
      name: "Le parcours express",
      promise: "Être à l'aise avec les bases en deux mois.",
      durationWeeks: 8,
      weeklyHours: 6,
      skills: ["Python", "SQL"],
      finalProject: "Un tableau de bord de tes dépenses",
      tradeoffs: ["Peu de théorie", "Pas de cloud"],
      boardId: "b1",
      chosen: false,
    },
    {
      id: "p2",
      rank: 2,
      name: "Le parcours solide",
      promise: "Comprendre les fondations pour tenir sur la durée.",
      durationWeeks: 16,
      weeklyHours: 7.5,
      skills: ["Python", "Statistiques", "SQL"],
      finalProject: "Une application complète avec sa base de données",
      tradeoffs: ["Long", "Moins de pratique au début"],
      boardId: null,
      chosen: false,
    },
    {
      id: "p3",
      rank: 3,
      name: "Le parcours projet",
      promise: "Apprendre en construisant une vraie chose.",
      durationWeeks: 1,
      weeklyHours: 10,
      skills: ["Docker"],
      finalProject: "Un service déployé",
      tradeoffs: ["Intense"],
      boardId: "b3",
      chosen: false,
    },
  ];
}
