# Bilan de la phase 5 (Étude)

Tag `phase-5`. 18 tâches, 37 commits depuis `phase-4`.
- **Revues par tâche** : sur Opus high pour les tâches à risque (5.1, 5.3, 5.4, 5.5, 5.6, 5.8, 5.9, 5.10, 5.11) ; les tâches front présentationnelles et les scripts sont couverts par la revue finale. Seules la 5.1 et la 5.9 ont demandé un round de correction.
- **Revue finale** : back en trois zones (agents, étude, programme / carte / capture), front en deux zones (étude, carte / replanification / capture), puis une vague de corrections par côté et une re-revue de chacune.
- **Tests** : back 2 839 passés, front 1 355, et parcours Playwright n° 1 réussi.

Contrôle de fin de phase sous Docker, avec GLM 5.3 flash, SearXNG, Gotenberg, Ollama et Qdrant réels (script `check_phase5`, 12 étapes) :
- **Essai de l'étude (5.7)** : 6 étapes sur 6 du premier coup. Séance guidée de 2 min 07, quiz de 12 questions écrit en 38 s et noté en 10 s. Aucune chaîne du quiz, des explications ou du bilan dans le journal du back.
- **1er essai complet** : le quiz est refusé (`retry_too_soon`), car le module avait déjà été tenté le matin. **Corrigé** : le script est relançable ; il prend un autre module libre et vérifie un bloc déjà fait au lieu de le refaire.
- **2e essai** : la séance guidée échoue en `node_timeout` au jugement de la 3e question finale. Le délai de 45 s du SDK ne borne que la connexion et chaque morceau d'une réponse en flux, jamais l'appel entier : une réflexion de GLM qui continue d'arriver n'était coupée qu'au plafond du nœud (120 s). **Corrigé** (D115 n° 17) :
  - échéance totale par appel pour tous les agents (`LLM_CALL_DEADLINE_S`, 600 s) ;
  - chaque appel du Tuteur a 105 s, avec un repli qui laisse la séance continuer : réponse non corrigée, indice sans texte, section telle qu'écrite dans la leçon, questions finales tirées des objectifs ;
  - la surcharge Z.ai (code 1305) est une panne passagère ; un quota épuisé ou une clé refusée restent des échecs visibles.

  Le correctif a demandé deux rounds de revue.
- **3e et 4e essais** (code final) : 11 étapes sur 12, sans avertissement ni repli. Le bilan hebdomadaire échoue comme attendu : le programme commence le 16/11.
- **Coût** : environ 0,025 $ pour une séance guidée (39 000 tokens en entrée), 0,003 à 0,01 $ pour un quiz, 0,001 à 0,002 $ pour une capture.
- **Parcours n° 1** : il échouait depuis la 5.12. Le tableau Excalidraw du Conseil bouclait (« Maximum update depth exceeded »). **Corrigé** dans 2d96ce6 : seule une scène vraiment modifiée relance l'attente de stabilisation (D116 n° 6).
- **Navigateur** : accueil (série, minutes de la semaine), carte des compétences et journal vus sur la pile réelle.

Décisions : D98 à D116 dans `DECISIONS.md`.

## Ce que la phase apporte

- **Session guidée (`study_session`, le Tuteur)** :
  - bloc du jour tiré du programme, minuteur, pause et reprise ;
  - section par section : explication, question, jugement (juste, partiel, faux), trois indices puis la solution, « Passer » ;
  - trois questions finales, bilan de séance ;
  - fin rangée une seule fois : temps, tâches du bloc cochées, compétences montées à `en_cours` au plus, une fiche par question manquée, ligne de journal ;
  - une session morte est rangée ou annulée au départ suivant.
- **Quiz (`quiz`, l'Examinateur)** :
  - QCM et réponses ouvertes notées sur barème, note sur 100 ;
  - 80 % en une passe pour `valide` ;
  - nouvel essai à J+2, fiches pour chaque erreur.
- **Révisions** : fiches à répétition espacée, raccourcis clavier, série de jours.
- **Replanification (`replan`, le Stratège)** :
  - bilan des retards et options (rattraper, alléger, repousser l'échéance) ;
  - avant / après du plan, versions du plan (`pending`, `superseded`, `empty`, `impossible`) ;
  - bilan hebdomadaire planifié le dimanche.
- **Carte de compétences** : graphe des prérequis (React Flow, ELK chargé à la demande), radar, courbe de progression (Recharts), comparaison avec une cible, détail avec les preuves.
- **Capture rapide (`capture`, l'Archiviste)** :
  - `Ctrl K` sur tout l'écran : lien, document ou texte collé ;
  - concepts extraits en étiquettes, rangés en mémoire ;
  - acquis déclaré seulement par la note de January ;
  - journal d'apprentissage filtrable.
- **Bout en bout** : modèles scriptés pour le Tuteur et l'Examinateur, script `check_phase5`.

## Arbitrages pris pendant l'exécution

- **Organisation** :
  - mode allégé : revue par tâche seulement pour les tâches à risque, revue finale complète ;
  - un seul implémenteur back à la fois ;
  - une tâche qui change le contrat ne tourne avec aucune tâche front ;
  - plage légère de 22 h 10 à 1 h, sans agent lourd.
- **Pré-vol** : 27 points de conflit (F1 à F27) tranchés avant la 1re tâche.
- **5.6** : des conteneurs pytest en double sont restés après un `docker kill` refusé à un agent ; le contrôleur ne l'a pas fait à sa place, et ils se sont arrêtés seuls.
- **5.9** : une nouvelle version du plan remplace toujours la précédente ; une version `pending` d'une session fermée se lit `superseded`.
- **5.11** : les concepts d'un lien, d'un document ou d'un texte collé deviennent des étiquettes de l'élément de mémoire.
- **Revue finale** : le back est revu en trois zones, son diff (1 Mo) ne tenant pas dans une seule revue. D115 regroupe les corrections ; le contrôle 5.18 passe en D116.
- **Front** : la date du nouvel essai d'un quiz est calculée côté navigateur, le back restant juge par `retry_too_soon`. La note de January n'est envoyée qu'avec « revoir ».
- **5.18** : les tâches cochées et le bilan hebdomadaire ne sont vérifiés en réel qu'à partir du 16/11 (voir plus bas). Jusque-là, les tests scriptés les couvrent.

## Revue finale et corrections

- **Back** : 0 Critical, 5 Important, corrigés dans 766dd73, 9d4cc06, 1356767, 0d50f98 et 752e6a6, avec 10 Minor et la cause back d'un Important du front. Re-revue approuvée.
  - Agents I1 : une réponse ouverte oubliée ou renumérotée par l'Examinateur valait 0 sans être redemandée.
  - Agents I2 : les fiches de capture gardaient une compétence donnée par une page non fiable, qui pouvait rétrograder un `valide`.
  - Étude I1 : une session morte après « Terminer » était annulée, et le temps, les tâches, le journal et la série étaient perdus.
  - Plan I1 : le rangement redatait toutes les tâches à faire.
  - Plan I2 : « Repousser l'échéance » ne faisait rien.
- **Front** : 0 Critical, 6 Important, corrigés dans 6e278b3 avec 9 Minor. Re-revue approuvée.
  - L'accueil bouclait sur « Reprendre ma session » après une session interrompue (cause back corrigée).
  - Le minuteur était perdu au rechargement.
  - « Refaire le quiz » s'affichait pendant les 2 jours d'attente.
  - Le message de fin de la replanification était perdu.
  - La note de January partait comme une demande de « revoir ».
  - Le report d'échéance était invisible.
  - Elkjs et Recharts sortent du chunk principal.
- **Contrôle réel** : 64c6520, 9eff58c et 1e6b2fa (le Tuteur continue quand le modèle ne répond pas), puis 2d96ce6 (tableau). Chacun relu et approuvé.

## Points laissés pour plus tard

### À vérifier en réel
- Tâches cochées par une séance ou un quiz : dès le lundi 16/11.
- Passage à `valide` par un quiz réussi : au nouvel essai, le 15/11.
- Bilan hebdomadaire : relancer `check_phase5` le dimanche 22/11.

### Phase 6
- Test `QuizPage` « preparation takes too long » instable sous la charge de la suite complète (attente de 1 s).
- Playwright ne s'arrête pas seul après un serveur e2e lancé par Docker (`E2E_BACKEND_COMMAND` via `sh`).
- Tokens d'un appel coupé non comptés dans le coût (déjà vrai pour `node_timeout`).

### Plus tard (mineurs triés « laisser », détail dans D115)
- Agents :
  - leçon entière renvoyée au Tuteur ;
  - première proposition sur un plan qui peut dater ;
  - plafonds de liste refusés au lieu d'être coupés ;
  - « Terminer » à la dernière question finale ne coche pas les lectures ;
  - une note renumérotée sur une vraie référence est mal attribuée.
- Étude :
  - erreur de quiz sur une fiche existante non ramenée au lendemain ;
  - révisions en double ;
  - série comptée à 0 minute ;
  - auteur du reflet d'une rétrogradation.
- Plan :
  - plafond « 5 heures » non gardé après l'acceptation ;
  - une capture peut cocher un quiz ;
  - retards de la dernière semaine jamais replanifiés ;
  - le rangement peut ouvrir une semaine « Suite » de trop.
- Carte : courbe moyenne qui baisse à l'arrivée de nouvelles compétences, couverture gonflée par des compétences hors catalogue, lectures N+1.
- Front :
  - route `/competences` chargée à la demande sans écran d'attente ni d'erreur ;
  - libellé « En pause » redondant.
- Reportés de la phase 4 et toujours ouverts : Brave jamais essayé en réel (aucune clé dans `.env`).
