/** Types de vue du diff d'un programme : indépendants du contrat d'API (D34). */

export interface PlanDiffTask {
  id: string;
  title: string;
  moduleTitle: string;
  /** Jour prévu ; `null` quand il n'est plus connu (tâche retirée). */
  plannedDate: string | null;
}

export interface PlanDiffMove {
  id: string;
  title: string;
  moduleTitle: string;
  from: string;
  to: string;
}

export interface PlanDiffView {
  added: PlanDiffTask[];
  removed: PlanDiffTask[];
  moved: PlanDiffMove[];
}
