# Bilan de la phase 2 (mémoire)

Tag `phase-2`. 13 tâches. Revues par tâche sur Opus high pour les tâches à risque : 2.2, 2.4, 2.7 et 2.8. Revue finale en deux parties, back et front, puis une vague de corrections et une re-revue. Tests : back 1 040 passés / 2 ignorés, front 512.

Contrôle de fin de phase sous Docker, avec Ollama bge-m3 et Qdrant réels :
- un PDF importé passe de « En cours » à « Indexé » en quelques secondes ;
- « Déjà appris » (GLM 5.3 flash) : l'Archiviste ajoute 5 acquis au niveau `declare`, suivis en direct ;
- la recherche « comment un modèle pondère les mots » trouve « Mécanisme d'attention » en tête (score 0,70) ;
- le détail de l'acquis montre l'auteur « Archiviste » et la raison « Document « cours-nlp » marqué « déjà appris ». » ;
- la carte 2D affiche les 6 points colorés par type ; les statistiques comptent 1 document et 5 acquis ;
- le journal du back ne contient ni contenu ni chaîne de requête.

Décisions : D60 à D70 dans `DECISIONS.md`.

## Ce que la phase apporte

- **Mémoire longue :**
  - éléments, fragments d'environ 500 tokens avec un recouvrement de 60, et un journal des écritures (agent, date, session, raison) ;
  - une seule collection Qdrant `memory`, filtrée par utilisateur ;
  - des vecteurs reconstructibles à tout moment par la réindexation.
- **Ingestion :**
  - formats : PDF, DOCX, Markdown, texte, URL, YouTube et texte collé ;
  - un worker unique, en série, qui reprend les imports au démarrage ;
  - un hash par utilisateur contre les doublons.
- **Lecteur web anti-SSRF :**
  - adresse vérifiée puis épinglée, revérifiée à chaque redirection ;
  - plafonds de 15 s et 20 Mo, `trust_env=False`.
- **Explorateur :**
  - liste filtrable, édition, suppression et fusion ;
  - recherche avec scores, banc d'essai, carte 2D PCA ;
  - statistiques (part du quota Vectorize), réindexation et export JSON.
- **Agents :**
  - port `MemoryGateway` et outils `memory_search`, `memory_write`, `memory_get_skills` ;
  - Archiviste « Déjà appris », qui crée des acquis au niveau `declare` ;
  - contexte mémoire réutilisable.
- **Moteur :** le statut final et l'événement final sont écrits en une seule transaction (D61).

## Arbitrages pris pendant l'exécution

- **Organisation :**
  - Jamais deux implémenteurs back en même temps (hook mypy et index git partagés) : un back et un front au plus.
  - Un commit commun pour 2.6 et la correction de 2.4.
- **2.2 :** si l'écriture finale échoue, 1 à 2 nouveaux essais courts, puis repli atomique en `failed` avec `outcome_not_written`. Le flux n'est fermé que si un commit a eu lieu.
- **2.4 :** le DoS PDF est un risque accepté (D63) ; le sous-processus avec délai est prévu au plus tard en phase 3.
- **2.6 :** une requête vide est refusée en 422 sans écho de la valeur reçue, et la propriété de l'élément est vérifiée avant le remplacement des fragments.
- **2.7 :**
  - le message de doublon ne cite pas le titre (17.2) ;
  - l'indexation suit l'ordre préparer → valider → pousser hors transaction → `indexed_at` court (D66) ;
  - le texte collé passe par `POST /documents/text` en JSON.
- **2.8 :** la réindexation suit D66 (drapeau, attente des écrivains, `indexed_at` conditionnel) et non le verrou prévu par le brief. Trois refus de fusion ont été ajoutés.
- **2.9 :** la tâche a démarré pendant la revue de 2.8 (lecture seule).
- **Revue finale :**
  - M3, le journal d'accès sans chaîne de requête, a été corrigé dans la vague ;
  - M7, la limite de 20 000 caractères d'un PATCH, est traité côté front : pour un document, seuls le titre et les étiquettes se modifient.

## Revue finale et corrections

- Back : 0 Critical, 4 Important, corrigés dans 14e68f0 avec M-T1 et M3, re-revue approuvée.
  - I1 : `hide_parameters` sur le moteur, plus de paramètres SQL dans les journaux.
  - I2 : titres et liste d'acquis encadrés par `untrusted()` avant d'arriver aux agents.
  - I3 : la réindexation sonde Ollama et Qdrant avant de vider l'index.
  - I4 : `indexed_at` remis à zéro dans la transaction de fusion et conditionnel en fin d'import.
  - M-T1 : la suppression valide en base avant de retirer les vecteurs.
  - M3 : le journal d'accès ne contient plus de chaîne de requête.
- Front : 0 Critical, 5 Important, corrigés dans 4e47e32, re-revue approuvée.
  - I1 : PATCH limité aux champs modifiés ; pour un document, seuls le titre et les étiquettes.
  - I2 : « Relancer » après un échec de « Déjà appris ».
  - I3 : panneau remonté pour chaque élément.
  - I4 : pagination recalée quand une page se vide.
  - I5 : fusion verrouillée pendant l'appel, avec une confirmation dans la page.

## Points laissés pour plus tard

### Phase 3
- `SessionView` sans `subject_id` : le suivi de l'Archiviste n'est pas repris après un rechargement, et une seconde session peut être lancée.
- DoS PDF : extraction dans un sous-processus avec délai, ou repli Gotenberg (D63).
- Titre de l'élément existant renvoyé sans cadre à l'agent quand l'écriture est un doublon (`memory_tools.py`).
- M2 : vecteurs orphelins si un document est supprimé pendant son import.

### Plus tard (mineurs triés « laisser »)
- M1 : délai de 300 s par job, trop court pour un très gros import sur un Ollama sans GPU.
- M4 : un document en erreur sans élément ne peut pas être supprimé.
- M5 : un document reste « erreur » après une réindexation réussie.
- M6 : une réindexation coupée par un redémarrage n'est pas relancée.
- Carte : au-delà de 20 000 vecteurs, `truncated` reste faux.
- Petits défauts de test (en-tête multipart sous jsdom, test de suppression instable une fois).
- Réindexation échouée au sondage : `total = 0` affiché.
