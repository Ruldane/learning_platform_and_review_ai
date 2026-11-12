/** Types de vue des composants du Conseil : indépendants du contrat d'API (D34). */

/** Les cinq étapes du Conseil (SPEC 3.1) : le cadrage mène au programme. */
export type CouncilStage = "framing" | "research" | "debate" | "proposals" | "program";

/** Commande du débat : un message sans texte que les agents lisent au tour suivant (D82). */
export type DebateCommand = "another_round" | "to_proposals" | "more_concrete" | "shorter";

/** Un parcours proposé par le Conseil (SPEC 3.2). */
export interface ProposalView {
  id: string;
  /** 1 pour la première proposition, 2 pour la suivante… */
  rank: number;
  name: string;
  promise: string;
  durationWeeks: number;
  /** Charge hebdomadaire, en heures (peut être fractionnaire : 7,5). */
  weeklyHours: number;
  skills: string[];
  finalProject: string;
  tradeoffs: string[];
  /** Tableau « comparaison » où la proposition est dessinée ; `null` s'il n'y en a pas. */
  boardId: string | null;
  /** Le parcours que January a choisi (un seul par lot). */
  chosen: boolean;
}

/** Les espaces à onglets de la page Conseil. */
export type CouncilTab = "board" | "sources" | "proposals";
