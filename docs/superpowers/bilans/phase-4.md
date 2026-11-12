# Bilan de la phase 4 (Conseil et programme)

Tag `phase-4`. 16 tâches, 33 commits depuis `phase-3`.
- **Revues par tâche** : sur Opus high pour les tâches à risque (4.1, 4.3, 4.4, 4.5, 4.6, 4.7, 4.10) ; en mode allégé pour les autres. La 4.4 (Mermaid du Scribe) a demandé quatre rounds de correction.
- **Revue finale** : en deux parties, back et front, puis une vague de corrections par zone et une re-revue de chacune.
- **Tests** : back 2 253 passés, front 1 002, et parcours Playwright n° 1 réussi.

Contrôle de fin de phase sous Docker, avec GLM 5.3 flash, SearXNG, Gotenberg, Ollama et Qdrant réels :
- **1er essai** : le Conseil échoue. GLM dépasse les plafonds de caractères des textes libres : 408 à 611 caractères pour 400 dans les bilans de tour, jusqu'à 701 pour 600 dans les notes de page. 4 pages sur 10 restent sans note. **Corrigé** : le texte libre trop long est raccourci au lieu d'être refusé (D97 n° 10).
- **2e essai** : le cadrage, le Conseil, le choix, le programme et la validation passent. La leçon de semaine 1 échoue ensuite : le Vérificateur relève à chaque passage 2 ou 3 nouvelles affirmations « non sourcées », dont une ligne d'objectif. **Corrigé** :
  - le Vérificateur ne juge plus que les sections de faits ;
  - après la 2e révision, le code retire lui-même les phrases encore non sourcées, puis rejoue les contrôles (D97 n° 11).

  Le même essai a révélé un second défaut : une session chaînée héritait du compteur de tokens de la session qui la lançait. `program_builder` montait ainsi à 312 000 tokens et faisait échouer la leçon suivante (D97 n° 12).
- **3e essai** : 8 étapes sur 9, puis le délai total du script (1 800 s) est dépassé pendant la chaîne des leçons, qui tourne en série à environ 5 minutes par leçon. Vérifié ensuite sur ce programme :
  - les 5 leçons des semaines 1 et 2 sont `ready` : 1 615 à 1 972 mots, PDF de 186 à 257 Ko, 4 à 6 ressources ;
  - une leçon a été élaguée d'une phrase ;
  - l'export PDF du programme et l'export `.ics` répondent ;
  - le journal du back (7 626 lignes) ne contient ni URL de page, ni texte d'objectif, ni erreur.

  Le délai par défaut du script passe à 3 600 s.
- **Coût** : environ 0,08 $ pour un Conseil complet (125 000 tokens en entrée).

Le correctif d23a6c7 (cas limites du retrait) a été relu et testé, mais n'a pas tourné en réel.

Décisions : D82 à D97 dans `DECISIONS.md`.

## Ce que la phase apporte

- **Conseil (`learning_council`)** :
  - cadrage en 5 questions au plus ;
  - recherche de l'Éclaireur : pages notées sur 100, praticiens jamais inventés ;
  - débat de 4 agents sur `1 + debate_rounds` tours, 150 mots au plus par prise de parole, citations `[n]`, objections tenues par le code ;
  - message de January repris nommément, commandes « Relancer un tour », « Passer aux propositions », « Plus concret », « Plus court » ;
  - 2 à 3 propositions, avec choix, mélange ou nouveau tour ;
  - trois points d'arrêt avec reprise exacte après redémarrage, sans double écriture au rejeu.
- **Tableau du Scribe** :
  - Mermaid analysé par une grammaire stricte puis réémis de façon canonique (sans retour arrière, pire cas 19 ms) ;
  - Excalidraw animé, avec repli SVG ;
  - retouches renvoyées aux agents ; exports PNG, SVG et `.excalidraw`.
- **Programme (`program_builder`)** :
  - Stratège, plafond de 85 % du budget, pratique et quiz chaque semaine ;
  - acquis sautés, ou révision de 20 minutes « déjà acquis » ;
  - vues Semaine, Liste et Avancement, déplacement à la souris et au clavier ;
  - validation, export PDF et `.ics`.
- **Leçons (`lesson_factory`)** :
  - Rédacteur et Vérificateur, Markdown de 1 200 à 2 500 mots, PDF A4 par Gotenberg avec sommaire, encadrés et Mermaid en SVG ;
  - Markdown nettoyé (markdown-it-py et nh3), CSP, seuls nos scripts figés s'exécutent (D89) ;
  - 3 à 6 ressources par module ;
  - production en chaîne, une leçon à la fois, avec au plus 3 essais par leçon ;
  - tâche planifiée toutes les 15 minutes pour les leçons à J-7.
- **Bibliothèque** : filtres, marque « Lue », copie locale des PDF libres, servie en `attachment`.
- **Relances** : un Conseil en échec se relance (`POST /goals/{id}/council`) ; un programme en échec se relance par « Choisir ».
- **Bout en bout** : modèles scriptés par agent, serveur e2e protégé, parcours Playwright n° 1, script `check_phase4`.

## Arbitrages pris pendant l'exécution

- **Organisation** :
  - jamais deux implémenteurs back en même temps ;
  - une tâche back qui change le contrat ne tourne avec aucune tâche front ;
  - le contrôleur recopie les décisions des rapports front.
- **4.4** : le filtrage du Mermaid par expressions régulières a été contourné deux fois, d'abord par un guillemet isolé, puis par `<br style=image-set>`. Il a été remplacé par une grammaire stricte avec réémission canonique. La première grammaire avait un ReDoS d'environ 4 minutes, corrigé par une analyse sans retour arrière.
- **4.6** : le court-circuit idempotent du choix passait avant le contrôle « Conseil en attente ».
- **4.7** : le reflet en mémoire est refait à chaque appel ; une seule règle de semaine (`rules.week_breaks`).
- **4.10** : la tâche J-7 passe toutes les 15 minutes au lieu de 6 heures. Une leçon interrompue s'affiche en échec à la lecture, sans écriture.
- **Windows** : Smart App Control bloque des DLL du `.venv`. Python et uv passent par Docker (remplaçants dans le scratchpad). `pnpm` est de nouveau utilisable sur l'hôte.
- **Docker Compose 5.5** : la construction par bake exige `--allow`. Les images sont donc construites par `docker build`, puis la pile démarre par `docker compose up -d --no-build` (D97 n° 16).

## Revue finale et corrections

- **Back** : 0 Critical, 2 Important, corrigés dans 53fc9ca avec M1, M3, M4, M5, M6 et une course de lecture. Re-revue approuvée.
  - I1 : un Conseil ou un programme en échec n'avait aucun chemin de relance.
  - I2 : du HTML brut non refermé avalait la fin d'une leçon. Le Vérificateur le refuse maintenant, et le rendu l'échappe.
- **Front** : 0 Critical, 3 Important, corrigés dans d619792 avec M1, M5, M6, M8, M10 et les boutons de relance. Re-revue approuvée.
  - I1 : « Envoyer mes modifications » était actif sans retouche.
  - I2 : le compteur de tours oubliait le tour 1.
  - I3 : les retouches étaient perdues quand le Scribe publiait un nouvel état.
- **Parcours n° 1** : 4 Important, corrigés dans 1c2ac56. Leçons des semaines 1 et 2 vraiment exigées, règles testées une à une, WebSocket réel, serveur e2e protégé.
- **Contrôle réel** : 643856d (textes raccourcis), eed6fb5 et d23a6c7 (convergence du Vérificateur, contexte vierge des sessions chaînées). Chacun relu et approuvé.

## Points laissés pour plus tard

### Phase 5
- Le titre d'une révision affiche le préfixe en double : « Réviser : Réviser Python appliqué… ».
- La semaine 1 du programme réel est peu chargée : 2 h 05 de tâches pour 11 h 54 disponibles. Il faut regarder comment le Stratège remplit le budget.
- Le formulaire de cadrage reste visible, avec ses champs vides, après la réponse.
- `check_phase4` arrête le contrôle sur une leçon `failed` alors que la production la relance jusqu'à 3 fois.
- Le Sceptique ne tient pas toujours la règle de l'objection après relance (vu au tour 1 en réel).
- Le bouton d'envoi du tableau compte sur un délai de 250 ms ; un chargement de police lent pourrait encore compter comme une retouche.

### Plus tard (mineurs triés « laisser »)
- Back :
  - rejeu de `save` qui republie ses événements ;
  - fenêtre de 409 avant `finalize` ;
  - N+1 de `list_goals` ;
  - `POST /sessions` peut lancer les parcours internes (à voir en phase 8) ;
  - dépendance croisée entre les features `program` et `lessons` ;
  - les praticiens servent de pages de départ à la recherche d'une leçon ;
  - `retry_council` efface le cadrage avant le lancement ;
  - abréviations hors liste dans le retrait (« Dr. ») ;
  - `[n]` orphelin en fin de paragraphe.
- Front :
  - `useLesson` relit sans limite une leçon `pending` ou `failed` ;
  - le focus reste en attente après un déplacement qui échoue ;
  - changer d'état du tableau fait perdre les retouches sans avertissement.
- Brave n'a toujours pas été essayé en réel : aucune clé dans `.env`.
