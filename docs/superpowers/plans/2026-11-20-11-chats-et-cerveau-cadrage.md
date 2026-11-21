# Phase 11 — Professeur dans la leçon, session training, cerveau synchronisé (cadrage)

> Cadrage issu de la séance de conception du 20/11 avec January. Le plan détaillé (tâches,
> tests) s'écrit au début de la phase, avec superpowers:writing-plans, à partir de ce cadrage.
> Ces trois features s'ajoutent aux reports de la 10b déjà prévus en phase 11 (plan directeur).

## Pourquoi

- **Étudier sans choisir une leçon d'abord.** Aujourd'hui, une séance d'étude commence par le
  choix d'une leçon. January veut ouvrir une séance libre et dire dans la conversation ce qu'elle
  veut réviser : une leçon, un mélange de deux ou trois, ou n'importe quel sujet de ses
  programmes.
- **Poser une question sur un passage sans quitter la leçon.** Comme le chat de VS Code : une
  fenêtre à côté du texte, pas un changement de page ni une nouvelle session à ouvrir.
- **Un « gros cerveau ».** Ses notes (aujourd'hui des coffres Obsidian, demain n'importe quoi)
  et ses programmes en cours réunis, interrogeables par un chat, et tenus à jour tout seuls quand
  elle ajoute ou retire des informations dans ses dossiers.
- **Tout pilotable par MCP**, comme le reste de Tremplin.

## Objectifs

1. **« Demander au professeur »** dans une leçon.
2. **Session training** dans Étudier.
3. **Cerveau** : dossiers synchronisés automatiquement et chat sur les documents et les
   programmes en cours.
4. **MCP** : les trois accessibles à Claude Code et à Codex, dans les limites des niveaux.

## Non-objectifs

- Pas de lecture d'images, d'audio ni de vidéo dans les dossiers (pas d'OCR) : ignorés et
  signalés dans le bilan.
- Pas d'écriture dans les dossiers de January : Tremplin lit, ne modifie jamais ses notes.
- Pas de synchronisation quand le PC est éteint ou le relais arrêté : elle reprend au démarrage.
- Pas de nouveau mode d'étude : les trois modes existants (socratique, Feynman, direct).

## Anti-objectifs (échec même si « ça marche »)

- Un chat qui répond sans dire d'où vient sa réponse (note, document, leçon).
- Une note supprimée ou modifiée dans Obsidian qui continue de nourrir les réponses.
- Un agent externe (MCP) qui fait lire à Tremplin un dossier que January n'a pas choisi.
- Une conversation qui consomme sans plafond ni affichage de la consommation.
- Un chat où chaque réponse attend 20 à 40 s alors que January n'a pas choisi le relais.

## Ce que January a décidé

- **Session training :**
  - le Tuteur ouvre la séance en demandant ce qu'elle veut faire ; le périmètre est libre (une
    ou plusieurs leçons, un sujet, plusieurs programmes) et peut changer en cours de séance ;
  - le Tuteur adapte sa conduite au mode choisi ;
  - **le mode se change pendant la séance**, sans la recommencer.
- **Cerveau :**
  - **synchronisation automatique** de **plusieurs dossiers** : ajout, modification et
    suppression de fichiers suivis tout seuls ;
  - contenu d'aujourd'hui : des notes Obsidian ; à terme : « tout et n'importe quoi ».
- **Synchronisation par un synchroniseur sur le PC, intégré au relais** (approche 1 ci-dessous).

## Approches de la synchronisation

| Approche | Pour | Contre |
| --- | --- | --- |
| **1. Synchroniseur dans le relais (retenue)** | Changements envoyés dans la seconde (surveillance native de Windows) ; dossiers ajoutés depuis Réglages ; le conteneur ne voit jamais le disque, il reçoit seulement les fichiers des dossiers choisis ; le relais démarre déjà à chaque connexion | Ne tourne que PC allumé et relais lancé ; un client de plus à appairer (s'appuie sur l'appairage du relais, déjà en phase 11) |
| 2. Dossiers montés en lecture seule dans le conteneur | Rien à installer sur le PC | Ajouter un dossier = éditer `.env` et redémarrer Docker ; Docker sous Windows ne relaie pas les notifications de changement, d'où une relecture périodique et du retard ; le conteneur a accès au disque |
| 3. Navigateur (File System Access, Chrome/Edge) | Rien à installer | Synchronise seulement onglet ouvert ; autorisation souvent redemandée ; Chromium seulement |

## Un moteur de conversation, trois portes

Les trois features reposent sur la même chose : **une conversation qui cherche dans la mémoire
avant de répondre**, avec des réponses en direct et des sources citées. Seuls changent le
périmètre et le rôle :

| Porte | Rôle | Périmètre de recherche | Qui mène |
| --- | --- | --- | --- |
| Professeur dans la leçon | Professeur | La leçon, le passage cité, puis la mémoire | January pose les questions |
| Session training | Tuteur | Les leçons et le contenu de ses programmes choisis dans la conversation | Le Tuteur mène (explique, questionne, indices) |
| Cerveau | Bibliothécaire | Ses documents synchronisés et ses programmes en cours | January pose les questions |

Le moteur est construit une fois (fil de messages, recherche, réponse en flux, sources, coût) et
ouvert à trois endroits. Le fil, la saisie et l'affichage markdown du chat de l'IDE
(`TeacherChat`, `ChatThread`, `ChatComposer`, `ChatMessage`, `ChatMarkdown`) passent dans
`frontend/src/shared/` pour servir aux trois (une feature n'importe pas une autre).

**Qui répond :** le modèle de Tremplin par défaut (réponse en flux, quelques secondes), ou
Claude Code / Codex par le relais, au choix avec le menu « Qui fait tourner les agents » (D218).
Le choix est celui de la conversation ; le temps de réponse du relais (20 à 40 s) est annoncé à
l'endroit du choix.

**Flux et sources (choix du cadrage) :** le texte de la réponse arrive en flux quand le
fournisseur le tient ; les sources arrivent ensuite en un bloc structuré, à la fin de la réponse.
Si le fournisseur ne tient pas le flux de façon fiable (GLM, D102 n° 6), la réponse arrive
entière d'un coup, avec ses sources : c'est un repli accepté.

**Coût (mêmes règles que le professeur de la phase 10) :** modèle léger par défaut, modèle fort
seulement sur demande ; contexte borné (passage, extraits retrouvés, derniers échanges, jamais
toute la mémoire) ; début de prompt fixe mis en cache ; plafond par conversation et par jour,
consommation affichée ; au plafond, réponses sur demande seulement.

## 1. « Demander au professeur » dans une leçon

- Sélectionner du texte dans une leçon fait apparaître un bouton **Demander au professeur** près
  de la sélection, aussi joignable au clavier.
- Il ouvre un **panneau de chat à droite, par-dessus la leçon** (pas de changement de page ni de
  route) : le passage est cité en tête, January écrit sa question, le professeur répond en
  connaissant la leçon, le passage et la mémoire.
- Le fil est **rattaché à la leçon** : plusieurs passages peuvent s'y succéder ; on ferme et on
  rouvre plus tard au même endroit.
- *Choix du cadrage :* ce bouton **remplace** l'actuel « Demander au tuteur » (`AskTutorBar`,
  D113 n° 2), qui ouvre une séance guidée sur `/etudier/session` : c'est précisément le
  changement de page que January ne veut plus. Le panneau garde un lien « Approfondir en
  séance » vers la séance guidée. La séance guidée par leçon (`study_session`, D102) reste telle
  quelle, sans migration vers le nouveau moteur.

```text
┌──────────── Leçon : Retriever sur le corpus ────────┬─ Professeur ───────── ✕ ┐
│ … le retriever renvoie les k passages les plus     │ « les k passages les    │
│ ▓▓proches du vecteur de la question▓▓ …            │   plus proches… »       │
│        [ Demander au professeur ]                  │ Toi : proche comment ?  │
│                                                    │ Prof : par similarité…  │
│                                                    │ [ Ta question…      ⏎ ] │
└────────────────────────────────────────────────────┴─────────────────────────┘
```

## 2. Session training (Étudier)

- Nouvelle entrée dans Étudier : **Session training**, sans choix de leçon préalable.
- Le Tuteur ouvre en demandant ce que January veut travailler ; il rassemble les leçons et le
  contenu correspondants, dans un ou plusieurs programmes ; le sujet peut changer en cours de
  route.
- Il conduit selon le mode (socratique, Feynman, direct), **modifiable à tout moment** dans la
  séance.
- La séance compte dans le temps d'étude et la série comme une séance actuelle ; les questions
  ratées deviennent des fiches de révision (point d'accroche « erreurs fréquentes » du plan
  directeur).
- *Choix du cadrage, effets sur les programmes :*
  - les fiches sont rattachées au module de la leçon travaillée ;
  - les compétences des modules travaillés montent au plus à `en_cours`, avec une preuve
    `study`, comme une séance guidée ;
  - le training **ne coche jamais** les tâches du planning : il n'est pas planifié, et cocher à
    tort fausserait le planning et la replanification ;
  - une seule séance d'étude ouverte à la fois, training ou séance de bloc
    (`uq_study_sessions_open` s'applique aux deux).

## 3. Cerveau : dossiers synchronisés et chat

**Dossiers :**

- Dans Réglages (ou la section Cerveau), January ajoute un ou plusieurs dossiers en collant leur
  chemin, leur donne un nom, peut les mettre en pause ou les retirer.
- Le synchroniseur (dans le relais) surveille ces dossiers et envoie à Tremplin les fichiers
  ajoutés ou modifiés et la liste des fichiers supprimés.
- Tremplin tient un document par fichier (dossier + chemin relatif + empreinte du contenu) :
  - fichier nouveau : ingéré ;
  - fichier modifié (empreinte changée) : réingéré, ses anciens extraits retirés de la recherche ;
  - fichier inchangé : ignoré ;
  - fichier supprimé, ou dossier retiré : ses extraits retirés de la recherche.
- Au premier passage d'un gros dossier : import en arrière-plan avec progression ; à la fin, un
  **bilan** (ingérés, ignorés et pourquoi, erreurs).

**Ce qui est lu :**

- **Obsidian** : les liens `[[note]]` deviennent des liens entre documents ; en-tête YAML et tags
  lus comme métadonnées ; `.obsidian/` ignoré ; les pièces jointes lisibles (PDF…) ingérées
  comme documents.
- Markdown, texte, PDF, DOCX (lecteurs existants de la mémoire, mêmes contrôles : 20 Mo, garde
  zip des DOCX) ; code et notebooks (`.py`, `.js`, `.ts`, `.ipynb`…) lus comme texte.
- Ignorés et signalés : images, audio, vidéo, binaires ; dossiers techniques (`.git`,
  `node_modules`, `.venv`…).

**Portée des notes synchronisées (décision de January, 20/11) :** les fichiers synchronisés
deviennent des **documents ordinaires de la mémoire**, comme ceux importés aujourd'hui : ils
apparaissent dans l'écran Mémoire et nourrissent **tous les agents** (contexte chargé par
`load_memory_context` : Tuteur, Conseil, CV…), pas seulement les trois portes. Les garde-fous
existants restent la seule protection : le contrôle d'honnêteté du CV contre le profil maître,
et les plafonds de niveau de la carte des compétences (une note ne monte jamais une compétence
au-delà de ce qu'un document importé permet aujourd'hui). Une note supprimée ou modifiée cesse
de nourrir les agents dès sa synchronisation.

**Chat du cerveau :** une section **Cerveau** avec ses dossiers, leur état de synchronisation et
le chat. Les réponses s'appuient sur les documents synchronisés et les programmes en cours, et
**citent leurs sources** (note, document ou leçon, avec un lien pour l'ouvrir).

## 4. MCP

- Exposé : lancer une session training et y parler ; poser une question au professeur sur un
  passage de leçon ; interroger le cerveau ; lire les conversations, l'état des dossiers et le
  bilan de synchronisation. Niveaux selon la règle existante (lecture 1 ; une conversation qui
  consomme le modèle de Tremplin se lance comme un parcours, avec la même limite de lancements).
- **Jamais exposé (niveau 4) :** ajouter, modifier ou retirer un dossier surveillé, et le canal
  par lequel le synchroniseur envoie les fichiers. Un agent externe ne doit pas pouvoir faire
  lire à Tremplin un dossier de son choix ni y injecter du contenu.
- Les rôles Professeur, Tuteur (training) et Bibliothécaire sont jouables par Claude Code ou
  Codex comme les autres agents (agents_play_*).
- *Choix du cadrage, contre quoi protéger :*
  - la limite tenue est celle des outils MCP ;
  - le synchroniseur s'authentifie par un **jeton de synchronisation distinct**, qui n'est pas
    un jeton MCP et n'ouvre que l'envoi de fichiers vers les dossiers enregistrés par January ;
  - un processus local sous le même compte Windows (Claude Code, Codex) peut déjà lire les notes
    sur le disque : s'en protéger est hors périmètre ;
  - le canal est un HTTP authentifié qui marcherait aussi vers un Tremplin hébergé (Cloudflare,
    visé à la fin). Dans ce cas, les notes quitteraient le PC : ce choix se tranchera au moment
    de l'hébergement, pas dans cette phase.

## Contraintes du dépôt

- Un dossier par feature des deux côtés, registres (`FEATURE_ROUTERS`, `MCP_FEATURES`, `GRAPHS`,
  `JOBS`, `app/registry.ts`) ; contrat OpenAPI d'abord ; tables par Alembic avec `user_id` et
  tests d'isolation ; garde de couverture MCP.
- Journaux : identifiants, nombres, codes, durées seulement. **Jamais un chemin de dossier, un
  nom de fichier, un texte de note ni un message de chat.**
- Aucun appel réel à un modèle ni au réseau dans les tests ; le synchroniseur testé avec
  `node:test` comme le relais.
- Interface accessible (bouton de sélection et panneau joignables au clavier, focus rendu à la
  leçon à la fermeture, animations coupées par `prefers-reduced-motion`).

## Laissé au constructeur

- Le découpage du moteur de conversation en graphe(s) et la forme de la conversation en base,
  tant que les trois portes partagent le même moteur.
- L'indexation du texte des leçons pour la recherche (aujourd'hui, les leçons écrivent des acquis
  dans la mémoire ; le training et le cerveau ont besoin de retrouver leur contenu).
- Le canal du synchroniseur vers Tremplin (route dédiée authentifiée par le jeton appairé du
  relais, envoi par lots, reprise après coupure), tant qu'il n'accepte que des fichiers de
  dossiers enregistrés par January et reste hors MCP.
- Le sort des acquis de mémoire tirés d'un document supprimé (retrait ou simple marque), à
  consigner en décision.
- Plafonds (taille d'un dossier, nombre de fichiers, tokens par conversation et par jour), à
  consigner en décision.

## Ordre proposé dans la phase

1. Moteur de conversation partagé et chat déplacé dans `shared/`.
2. « Demander au professeur » (la porte la plus simple, valide le moteur).
3. Session training.
4. Cerveau : dossiers, synchroniseur dans le relais, ingestion Obsidian, chat.
5. MCP des trois portes, puis essai réel (modèle de Tremplin et relais) sur une pile jetable.
