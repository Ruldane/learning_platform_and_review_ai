# Tremplin specification

Nov 11, 2026 · @January

## 1. Vision and approved decisions

Tremplin combines AI-guided learning and job search in one local app. Both use a shared memory
of what January already knows. Claude Code can use this specification directly.

**Product principles**

- **Live progress.** Long actions show agents debating, researching, or drawing in real time.
- **Human approval.** January expressly approves programs, CVs, and messages before finalization.
- **Shared memory.** Learning, imports, and decisions feed one store that every agent can read.
- **Accuracy.** Agents rephrase and tailor content without inventing experience, degrees, or
  figures. They cite the source of every claim drawn from the web.
- **Costs limited to models.** The rest runs on open-source software in Docker.
- **Code organization.** The `frontend` and `backend` directories hold files of up to 300 lines.

**Approved decisions**

| Topic | Decision |
| --- | --- |
| Deployment | Local Docker first, Cloudflare later |
| Backend | Python, FastAPI, LangChain, and LangGraph |
| LLM providers | Anthropic, OpenAI, and GLM, selected in the UI. Haiku by default |
| Sign-in | Google OAuth, disabled by default locally |
| Web search | Free and self-hosted (section 10) |
| Vector database | Open source in Docker, native equivalent on Cloudflare (section 4) |
| Embeddings | Local model served by Ollama |
| CV | PDF as the only source. Recreate the design once as a reusable template |
| LinkedIn | Profile PDF export or pasted text only. No automated access |
| Study time | 10 to 15 hours weekly, with 2 hours each weekday and a weekend block |
| Interface | Light theme only |
| Scope | All 19 features in section 2 are in the MVP |
| Manual configuration | LLM provider API keys only |

**Initial assumptions**

- The dictated phrase “Echo la main” refers to **Ollama**.
- D312 sets English for the interface and newly generated lessons. Sources can use any language.
- UI strings are centralized. Existing lessons and other stored prose retain their language.
- The repository codename is `tremplin`. The public name was open in the original proposal.

## 2. MVP scope

The MVP covers 19 features. Seven are core, six were approved in discussion, and six were added.

| No. | Feature | Description | Section |
| --- | --- | --- | --- |
| F1 | Learning Council | Four agents debate the goal live with web research and a whiteboard | 3 |
| F2 | Program | Weekly schedule, task list, lesson PDFs, and downloadable resources | 3 |
| F3 | Vector memory | Agents read and write imports and skills in an explorable store | 4 |
| F4 | CV Review | Two agents tailor the CV to a posting and render it in the same design | 5 |
| F5 | Application tracking | Pipeline, suggested follow-ups, and duplicate alerts | 6 |
| F6 | Model settings | Provider and model per role, plus API key management | 11 |
| F7 | Google sign-in | A space for each user, optional locally | 17 |
| F8 | Skill gap assessment | Compare postings with skills and add gaps to the plan | 7 |
| F9 | Skill validation | Quizzes and spaced reviews before marking a topic as learned | 7 |
| F10 | Mock interview | Posting-based technical and behavioral interview | 7 |
| F11 | Proof projects | A small project per module yields a CV line and draft post | 7 |
| F12 | Market radar | Analyze postings for the target role to prioritize skills | 7 |
| F13 | Adaptive replanning | Weekly review and revised schedule | 7 |
| F14 | Guided study | A tutor supports each study block in real time | 8 |
| F15 | Skill map | Graph of mastered, ongoing, and missing skills with evidence | 8 |
| F16 | Application kit | Tailored CV, letter, messages, and company dossier in one click | 8 |
| F17 | Morning brief | Live home page with study, reviews, follow-ups, and new postings | 8 |
| F18 | Quick capture | Turn a link, PDF, or note into a summary, flashcards, and memory | 8 |
| F19 | Hiring panel | Four recruiter personas discuss the CV against the job posting | 8 |

The MVP excludes a mobile app, automated submissions or messages, automated LinkedIn access,
voice mode, and payments.

## 3. Learning workflow (F1 and F2)

January enters a goal and four agents debate it live. She selects a learning path and Tremplin
produces a full program with lessons and resources.

### 3.1 Session flow

1. **Goal.** January enters a free-text goal such as becoming an AI product engineer, an
   optional deadline, and her time budget. The Moderator reads memory and asks up to five
   clarifying questions.
2. **Research.** The Scout searches the web (section 10). Each selected source appears live
   in the Sources panel with its author, date, and language.
3. **Opening round.** Each agent posts a position in up to 150 words. The Scribe draws a domain
   map on the whiteboard.
4. **Later rounds.** Agents respond to and challenge each other before converging. The default
   is three rounds, configurable from one to five.
5. **Proposals.** The Council presents two or three paths. Each has a name, expected outcome,
   duration in weeks, weekly workload, skills, final project, tradeoffs, and whiteboard diagram.
6. **Choice.** January chooses one path, combines two, or asks for another round. For another
   round, return to step 4.
7. **Program.** The Strategist makes a weekly plan. January can move, remove, or add items
   before approving it.
8. **Production.** Lessons and resources are produced in the background. Weeks one and two
   are produced immediately. Later weeks are produced seven days in advance to allow replanning.

### 3.2 January's role

- The message field stays available throughout the debate. The next round includes the message,
  and the agents must address it explicitly.
- Controls remain visible for pausing, starting another round, moving to proposals, asking for
  more concrete details, and asking for shorter replies.
- The session waits for January after the goal questions, at path selection, and at program
  approval.
- An interrupted session resumes at the same point, including after a Docker restart.

### 3.3 Animated whiteboard

- The whiteboard is an Excalidraw canvas with a hand-drawn classroom style.
- The Scribe emits a Mermaid `flowchart`. The frontend converts it to Excalidraw elements
  with `@excalidraw/mermaid-to-excalidraw`.
- Elements appear in reasoning order with 150 to 300 ms between them.
- Diagrams include domain maps, prerequisite graphs, path timelines, and proposal comparisons.
- January can move, annotate, and correct the board. Agents receive her edits as a message.
- Every board state is saved. Exports are available as PNG, SVG, and `.excalidraw`.
- If conversion fails, the frontend displays Mermaid's SVG and logs the error.

### 3.4 Program (F2)

A program contains weeks, weeks contain modules, and modules contain tasks.

| Level | Required fields |
| --- | --- |
| Week | Theme, measurable goal, hours, end-of-week deliverable |
| Module | Title, target skills, prerequisites, linked lesson and resources |
| Task | Action title, type, 15 to 120 minute duration, completion criterion, scheduled day |

Task types are `read`, `watch`, `practice`, `quiz`, and `project`.

**Scheduling rules**

- The default is two hours each weekday and one three- to four-hour weekend block. January
  can change availability in Settings.
- Planned work uses at most 85% of the budget to leave room for interruptions.
- Skip a topic memory already knows, or make it a 20-minute review labeled **Already known**.
- Each week includes at least one practice task and ends with a quiz (F9).
- Views include a weekly calendar, full list, and overall progress. Export to PDF or `.ics`.

### 3.5 Lessons

- Each module has one lesson stored as Markdown, readable in the app and downloadable as a PDF.
- Lessons are 1,200 to 2,500 words.
- Each lesson includes up to three objectives, prerequisites, a five-line summary, explanation,
  diagrams, a worked example, common mistakes, an exercise and separate answer, sources, and
  a five-question self-assessment.
- The Writer drafts the lesson. The Checker verifies facts against retrieved sources and
  checks links. The lesson paraphrases the sources and uses short, attributed quotes.
- A shared A4 HTML and CSS template provides a contents list, callouts, Mermaid diagrams as
  SVG, page numbers, and a light theme.

### 3.6 Resources

- Each module has three to six resources.
- Each has a type (official documentation, course, video, article, repository, or paper),
  language, duration, level, author, date, and a one-sentence reason for choosing it.
- Freely downloadable PDF papers and docs are saved locally. For other resources, keep the
  link and its reading entry.
- Library lists resources with filters for program, type, language, and read status.

## 4. Vector memory (F3)

January and the agents read and write memory through a local vector database. The relational
database retains the source text so the vector index can be rebuilt at any time. [Qdrant]

### 4.1 Technology

| Component | Local Docker | Future Cloudflare deployment |
| --- | --- | --- |
| Vector store | `qdrant/qdrant` Docker image, under Apache 2.0 | Vectorize |
| Embeddings | Multilingual `bge-m3` on Ollama, 1,024 dimensions | `@cf/baai/bge-m3` on Workers AI |
| Code interface | `MemoryRepository` backed by LangChain's `VectorStore` | `MemoryRepository` |

The same embedding model keeps the dimensions and search behavior consistent when migrating.
`bge-m3` supports over 100 languages, including French and English.

A shared interface makes the implementations portable. The original plan estimated that the
free Vectorize allowance of five million dimensions would fit about 4,880 chunks at 1,024
dimensions each. Beyond that, the design calls for a paid plan or a smaller model and the
reindex operation in section 4.6. [Vectorize pricing][vectorize-pricing]

[Qdrant]: https://github.com/qdrant/qdrant
[vectorize-pricing]: https://developers.cloudflare.com/vectorize/platform/pricing/

### 4.2 Organization

Qdrant uses one `memory` collection, filtered by `user_id` and `kind`.

| `kind` | Content | Writers |
| --- | --- | --- |
| `document` | Chunks from CVs, LinkedIn exports, notes, PDFs, and saved web pages | January |
| `skill` | One point per concept or skill with mastery and evidence | January, agents, quizzes |
| `lesson` | Chunks of generated lessons | Agents |
| `source` | Summaries of web sources for reuse | Agents |
| `posting` | Job postings and company dossiers | January, agents |
| `decision` | Preferences and decisions, such as favoring practice over videos | January, agents |

Common payload fields are `user_id`, `kind`, `source_id`, `title`, `text`, `lang`, `tags`,
`created_by`, `created_at`, and `session_id`.

**Skill mastery levels**

| Level | Condition |
| --- | --- |
| `declared` | January reports the skill or it is extracted from an imported document |
| `in_progress` | A module in the current program covers the skill |
| `validated` | January passes a quiz with 80% or higher (F9) |
| `proven` | A completed project uses the skill (F11) |

### 4.3 Ingestion

- Accept PDF, DOCX, Markdown, text, URLs, YouTube transcripts, and pasted text.
- Extract and clean text, split it into roughly 500-token chunks with a 60-token overlap, embed
  the chunks, and save them.
- A content hash prevents duplicate indexing.
- Each document shows its processing status as queued, in progress, indexed, or failed.
- January can mark a document as already learned. The Archivist extracts its concepts as
  `declared` skills.

### 4.4 Agent reads

- `memory_search(query, kinds, k)` performs dense search filtered by `kind`, with eight results
  by default.
- `memory_get_skills()` summarizes the skill map (F15).
- Each agent graph starts by loading relevant skills, decisions, and documents for the goal.

### 4.5 Agent writes

- Agents write through `memory_write(kind, title, text, tags, evidence)`.
- Agents can write `source` and `lesson` entries directly.
- Agent-written skills start at `declared` or `in_progress`. A quiz or project can raise the level.
- A proposed `decision` waits under **To confirm** before being saved.
- Each write records the agent, date, session, and a one-sentence reason.

### 4.6 Memory explorer

The Memory page shows what agents know about January.

- **List.** Filter by type, tag, author, and date. Edit, delete, and merge duplicates.
- **Semantic search.** View matching results with their scores.
- **Entry details.** Read the text, chunks, metadata, nearest neighbors, and write history.
- **2D vector map.** The backend projects vectors with PCA by default. Colors identify types
  and clicking a point opens its entry.
- **Query preview.** See the exact chunks an agent would receive for a query.
- **Statistics.** View totals by type, the last write, and estimated Vectorize quota usage.
- **Actions.** Rebuild vectors from text, export JSON, or open the Qdrant dashboard at
  `http://localhost:6333/dashboard`.

## 5. CV Review (F4)

Deux agents relisent le CV face à une offre précise, proposent des modifications justifiées, puis régénèrent le PDF dans le design d'origine si January le demande.

### 5.1 Profil maître (une seule fois)

- January importe son CV en PDF, l'export PDF de son profil LinkedIn (ou un copier coller), et un texte libre sur ce qu'elle sait faire et ce qu'elle vise.
- L'Archiviste en tire un **profil maître** structuré en JSON : identité, titre, résumé, expériences avec réalisations, formation, compétences, projets, langues, liens.
- January relit et corrige ce profil dans un formulaire.
- Le profil maître est la seule source de faits. Tout CV ciblé en est un sous ensemble reformulé.

### 5.2 Capture du design (une fois par design)

1. Le back end extrait du PDF les blocs de texte avec position, police, taille et couleur, ainsi qu'une image de chaque page.
2. Le Maquettiste, un agent avec un modèle de vision, produit un template HTML et CSS qui reproduit la mise en page : colonnes, marges, couleurs, hiérarchie.
3. Le template est rendu en PDF, puis comparé à l'original. L'écran montre les deux côte à côte avec un score de ressemblance. Trois passes de correction automatique au maximum.
4. January valide, ou demande un ajustement en langage naturel (exemple : la colonne de gauche est trop large).

- **Polices.** Si la police d'origine est libre, elle est téléchargée dans le dossier du template. Sinon, la plus proche est utilisée et l'écart est signalé.
- **Limite assumée.** Le rendu est fidèle, pas identique au pixel près.

### 5.3 Revue ciblée sur une offre

L'entrée est un lien vers l'offre ou son texte collé. Si le lien ne peut pas être lu (connexion requise, page vide), l'application le dit tout de suite et demande le texte. Aucune analyse ne démarre sur une offre devinée.

1. **Analyse de l'offre.** Intitulé, niveau, exigences obligatoires et souhaitées, mots clés dans leur formulation exacte, critères éliminatoires (années d'expérience, lieu, langue), outils.
2. **Recherche entreprise.** Produit, stack, actualité, valeurs, processus de recrutement, et logiciel de recrutement utilisé quand l'adresse de candidature le révèle.
3. **Contrôle doublon.** Vérification dans le suivi de candidatures (section 6).
4. **Lecture machine**, par le Lecteur ATS. Il extrait le texte du PDF comme le ferait un parseur, puis vérifie l'ordre de lecture, les intitulés de sections, la présence des mots clés et leurs variantes.
5. **Lecture humaine**, par le Recruteur. Clarté du premier écran, adéquation du titre, réalisations chiffrées, ordre de pertinence, signaux d'alerte, longueur.
6. **Confrontation.** Les deux agents arbitrent leurs désaccords en deux tours visibles au maximum (densité de mots clés contre lisibilité).
7. **Propositions.** Chaque modification indique : section, avant, après, raison, type, et le fait du profil maître sur lequel elle s'appuie. January accepte ou refuse chacune, ou tout d'un coup.
8. **Sortie au choix.** Soit un rapport « quoi modifier », soit le CV généré en PDF avec le template et les modifications acceptées.
9. **Contrôle final.** Le PDF généré est relu par le Lecteur ATS. Le nombre de pages reste celui de l'original, sauf accord.

Le fichier est nommé `CV_<Nom>_<Entreprise>_<Poste>.pdf`, versionné, et lié à la candidature.

**Deux indicateurs affichés, avant et après**

| Indicateur | Calcul |
| --- | --- |
| Couverture des exigences | Part des exigences obligatoires de l'offre couvertes par un fait réel du CV |
| Lisibilité machine | Liste de contrôles réussis : texte sélectionnable, ordre de lecture, intitulés standards, coordonnées dans le corps, tailles de police |

Ces indicateurs sont internes à l'application. L'écran précise qu'il n'existe pas de score ATS universel.

### 5.4 Ce que les agents savent des logiciels de recrutement

Les agents partent d'une base de connaissances datée, rafraîchie par une recherche web tous les 30 jours. Point de départ, tiré de l'[enquête de Huntr](https://huntr.co/blog/how-applicant-tracking-systems-work) :

- Un ATS est surtout une base de candidatures avec un moteur de recherche. D'après cette enquête, aucun grand ATS ne rejette seul un CV sur son contenu.
- Le vrai filtre automatique, ce sont les questions éliminatoires du formulaire. Le Kit de candidature (F16) les repère et prépare des réponses exactes.
- Les mots clés servent à la recherche et au classement par les recruteurs. Certains ATS ajoutent un classement par IA.
- Côté forme : coordonnées hors en tête et pied de page, polices standards de 10 points ou plus, fichier PDF ou Word.

**Règles appliquées par les agents**

- Reprendre les termes exacts de l'offre partout où ils sont vrais pour January.
- Intitulés de sections standards, ordre chronologique inversé, dates homogènes, aucun texte dans une image.
- Jamais de texte caché ni de bourrage de mots clés.
- Aucune garantie de passage n'est affichée, seulement les contrôles réussis.

### 5.5 Garde fous

- Un nœud validateur compare chaque phrase proposée au profil maître. Tout outil, chiffre ou titre absent du profil bloque la modification, qui passe en « à confirmer ».
- Si January confirme un fait nouveau, il est d'abord ajouté au profil maître.
- Un mot clé de l'offre que January ne maîtrise pas n'entre pas dans le CV. Il part vers l'analyse d'écart (F8).

## 6. Suivi de candidatures (F5)

L'onglet Candidatures tient le registre de chaque offre, propose les relances au bon moment et bloque les doublons.

### 6.1 Fiche candidature

- **Champs.** Entreprise, poste, lien de l'offre, copie figée du texte de l'offre, canal, date de candidature, statut, version du CV envoyé, lettre, contacts (nom, rôle, lien), notes, prochaine action et sa date.
- **Statuts.** À postuler, Postulée, Relancée, Entretien, Offre, Refus, Sans réponse, Retirée.
- **Vues.** Kanban par statut, tableau triable, et fil chronologique des événements sur chaque fiche.
- La copie du texte de l'offre est prise à la création, car les annonces disparaissent.

**Trois façons de créer une fiche**

1. Automatiquement, quand un CV est généré pour une offre. La fiche naît au statut À postuler, et le bouton « J'ai postulé » fixe la date.
2. À la main, par un formulaire.
3. En langage naturel : « j'ai postulé hier chez X pour le poste Y ». L'Assistant de suivi crée la fiche et la montre pour confirmation.

### 6.2 Relances

| Déclencheur | Suggestion |
| --- | --- |
| 7 jours après la candidature, sans réponse | Message LinkedIn au recruteur ou au responsable du poste |
| 14 jours, sans réponse | Relance par email |
| 21 jours, sans réponse | Proposer de classer la fiche en Sans réponse |
| Lendemain d'un entretien | Message de remerciement |
| 7 jours après un entretien, sans réponse | Demande de nouvelles |

- Les délais sont modifiables dans les réglages.
- Chaque relance affiche qui contacter, un brouillon prêt à copier, et trois boutons : Fait, Reporter de 3 jours, Ignorer.
- Sans contact enregistré, la relance propose un lien de recherche LinkedIn pré rempli (entreprise et rôle).
- L'application n'envoie jamais rien elle même. January copie et envoie.
- Les relances dues remontent dans le Brief du matin (F17) et en pastille sur l'onglet.

### 6.3 Alerte doublon

Le contrôle se déclenche dès qu'une offre entre dans l'application, quel que soit l'écran.

| Niveau | Condition |
| --- | --- |
| Certain | Même lien, après normalisation de l'adresse |
| Probable | Même entreprise et intitulé similaire à 85 % ou plus |
| Possible | Même entreprise et texte d'offre très proche selon la recherche vectorielle |

- Message type : « Attention, tu as déjà postulé chez X pour le poste Y le 3 novembre (statut : Postulée). »
- Choix proposés : ouvrir la fiche existante, confirmer que c'est un autre poste, annuler.
- Une candidature chez la même entreprise pour un autre poste dans les 30 jours déclenche une simple information.

### 6.4 Indicateurs

L'onglet affiche le nombre de candidatures par statut, le taux de réponse, le délai moyen de réponse et le nombre de relances dues.

## 7. Les six features validées (F8 à F13)

Ces six features relient l'apprentissage et la recherche d'emploi : ce qui manque pour une offre devient du programme, et ce qui est appris devient une preuve sur le CV.

### F8. Analyse d'écart

- **Déclencheur.** Toute offre ajoutée, ou à la demande sur un poste cible.
- **Fonctionnement.** L'Analyste extrait les compétences de l'offre, les rattache au référentiel de compétences, puis les compare aux acquis.
- **Sortie.** Un tableau par compétence : exigée ou souhaitée, niveau actuel, action proposée (déjà au programme en semaine N, à ajouter, hors périmètre).
- **Score de match** de 0 à 100. Une exigence obligatoire pèse 2, une souhaitée pèse 1. Un acquis `valide` ou `prouve` compte 1, `declare` 0,6, `en_cours` 0,3, absent 0.
- Le bouton « Ajouter au planning » lance une replanification (F13), toujours soumise à validation.
- Une vue agrégée montre les 10 compétences qui manquent le plus souvent sur l'ensemble des offres.

### F9. Validation des acquis

- L'Examinateur génère un quiz par module : 8 à 12 questions qui mêlent QCM, réponse courte, lecture de code et « explique avec tes mots ».
- Les réponses ouvertes sont notées avec une grille, et chaque erreur reçoit une explication.
- À 80 % ou plus, l'acquis passe à `valide`. En dessous, des tâches de révision ciblées sont ajoutées, avec un nouvel essai 2 jours plus tard.
- **Révisions espacées.** Des fiches sont créées depuis les leçons et les erreurs de quiz. Intervalles de 1, 3, 7, 16 puis 35 jours. Une erreur ramène la fiche à 1 jour.
- La file de révision du jour est plafonnée à 15 minutes.
- Un acquis `valide` dont les fiches échouent deux fois de suite redescend à `en_cours`.

### F10. Simulateur d'entretien

- Lancé depuis une candidature, ou librement sur un poste.
- **Modes.** Comportemental, technique, étude de cas, mixte. Durée de 15, 30 ou 45 minutes. En français ou en anglais.
- L'Intervieweur pose une question à la fois et relance selon les réponses. Il s'appuie sur l'offre, le dossier entreprise, la version du CV envoyée et les écarts connus.
- Échange par écrit dans le MVP.
- **Débrief.** Note par critère (clarté, structure, profondeur technique, adéquation au poste), 3 points forts, 3 points à corriger, et une version améliorée de la réponse la plus faible.
- Les questions ratées deviennent des fiches de révision. Le débrief est rattaché à la candidature.

### F11. Projets preuves

- Chaque module se termine par un mini projet de 3 à 6 heures : contexte, objectif, contraintes, critères d'acceptation.
- January soumet un lien de dépôt, ou une description avec captures.
- Le Praticien évalue le rendu contre les critères et donne un retour écrit.
- À la validation, l'acquis passe à `prouve` et quatre brouillons sont générés : une ligne de CV, une entrée de projet pour le profil maître, un post LinkedIn, un plan de README.
- Rien n'entre dans le profil maître sans validation.
- Un écran Portfolio liste les projets et leur statut.

### F12. Radar du marché

- Chaque semaine, et à la demande, l'Éclaireur collecte 30 à 50 offres publiques pour le poste et la zone visés.
- L'Analyste en extrait compétences, outils, niveau, télétravail, et salaire quand il est affiché.
- **Sortie.** Classement des compétences par fréquence, évolution depuis le dernier relevé, et alertes du type « demandée dans 60 % des offres, absente de ton programme ».
- Les offres dont le score de match atteint 70 remontent dans le Brief du matin.
- Le rapport indique toujours combien d'offres ont réellement été lues. Les sites qui bloquent la lecture sont comptés à part.

### F13. Replanification adaptative

- **Bilan hebdomadaire** le dimanche à 18 h, heure réglable : heures prévues et faites, tâches terminées, résultats de quiz.
- Le Stratège propose un nouveau plan. Les tâches en retard sont redistribuées sans jamais dépasser le budget hebdomadaire.
- Plus de 30 % de retard deux semaines de suite : deux options sont présentées, réduire le périmètre ou repousser l'échéance.
- En avance : avancer la suite, ou approfondir.
- **Autres déclencheurs.** Ajout depuis l'analyse d'écart, ou message du type « cette semaine je n'ai que 5 heures ».
- Chaque proposition montre l'avant et l'après, attend une validation, et l'historique des versions du plan est conservé.

## 8. Six nouvelles features (F14 à F19)

Ces six ajouts rendent la plateforme vivante au quotidien : un tuteur pendant l'étude, une page d'accueil qui bouge chaque matin, et un comité qui juge le CV avant les vrais recruteurs.

### F14. Session d'étude guidée

- Le bouton « Commencer mon bloc » ouvre la session du jour avec un minuteur. Cycles de 50 minutes de travail et 10 de pause par défaut, réglables.
- Le Tuteur mène le bloc : objectif, leçon section par section, une question de compréhension après chaque section, l'exercice, puis 3 questions finales.
- **Trois modes.** Socratique (il questionne pour faire trouver), Feynman (January explique, il cherche les trous), Direct (il répond).
- Le bouton « Je bloque » donne trois niveaux d'indices avant la solution.
- Le Tuteur connaît la leçon, ses sources et la mémoire. Il peut dessiner au tableau.
- **Fin de session.** Résumé, temps enregistré, tâches cochées, acquis mis à jour, fiches créées depuis les erreurs, une ligne dans le journal.
- La série de jours consécutifs et les heures de la semaine sont visibles en permanence.

### F15. Carte de compétences vivante

- Un graphe où chaque nœud est une compétence et chaque lien un prérequis. La couleur indique le niveau de maîtrise, la taille la demande du marché (F12).
- Le référentiel est créé par le Stratège à la création du programme, puis enrichi par les offres et le Radar.
- Un clic sur un nœud montre les preuves (leçons, quiz, projets, lignes de CV), les offres qui l'exigent et la prochaine action.
- **Trois vues.** Graphe, radar par domaine, courbe de progression avec un relevé par semaine.
- **Comparaison.** Moi aujourd'hui, le poste cible, ou une offre précise.
- C'est la référence unique lue par F4, F8, F12 et F13.

### F16. Kit de candidature

Pour une offre, un clic génère en parallèle sept pièces, chacune affichée dès qu'elle est prête.

| Pièce | Détail |
| --- | --- |
| CV ciblé | Parcours de la section 5 |
| Lettre de motivation | 250 à 350 mots, dans la langue de l'offre |
| Messages LinkedIn | Une version courte pour l'invitation, une version longue pour le message |
| Emails de relance | Brouillons pour 7 et 14 jours |
| Réponses au formulaire | Questions éliminatoires repérées, réponses tirées du profil maître uniquement |
| Dossier entreprise | Une page sourcée : activité, produit, stack, actualité des 6 derniers mois, culture, processus d'entretien, 5 questions à poser, points de vigilance |
| Pitch de 60 secondes | « Parle moi de toi » adapté au poste |

- Tout est modifiable avant usage, enregistré sur la fiche candidature, et exportable en une archive.
- Un **guide de style personnel**, saisi en texte libre dans les réglages, s'applique à tous les textes écrits au nom de January.
- Les prétentions salariales ne sont jamais remplies par un agent.

### F17. Brief du matin

- Généré chaque jour à 7 h, heure réglable, et à l'ouverture de l'application s'il date de la veille.
- **Contenu.** Bloc d'étude du jour, fiches à réviser, relances dues, nouvelles offres du Radar, avancement de la semaine, une ressource ou actualité sourcée du domaine visé, et deux phrases du conseil sur la priorité du jour.
- La page d'accueil est ce brief, avec quatre actions rapides : Commencer mon bloc, Réviser, Ajouter une offre, Capturer.
- Un fil d'activité montre ce que les agents ont fait en tâche de fond : leçons générées, relevé du Radar, écritures en mémoire.

### F18. Capture rapide

- Un champ global, ouvert par Ctrl K ou Cmd K, accepte un lien, un texte, un fichier ou une note du type « j'ai appris X aujourd'hui ».
- L'Archiviste lit, résume en 5 lignes, extrait les concepts, les relie aux modules du programme, et range le tout en mémoire.
- Si la capture couvre une tâche planifiée, il propose de la cocher. Il propose aussi des fiches de révision.
- Si un lien ne peut pas être lu, l'application le dit tout de suite et demande le texte.
- Le **journal d'apprentissage** réunit captures, sessions et quiz dans un fil chronologique consultable, avec un résumé hebdomadaire.

### F19. Comité de recrutement simulé

- **Entrée.** Une version du CV et une offre.
- **Quatre personas.** Le filtre machine (quelles recherches de recruteur feraient remonter ce CV), la recruteuse RH, le manager du poste, le futur collègue.
- Chacun donne sa première impression, puis le comité débat en direct pendant deux tours, puis vote : entretien oui, non ou peut être, avec son objection principale.
- **Sortie.** Verdict, objections classées, et les 3 changements qui feraient basculer un vote.
- Relancer le comité après correction montre l'avant et l'après.
- Les personas s'adaptent à l'entreprise grâce au dossier entreprise (startup ou grand groupe).
- L'écran précise qu'il s'agit d'une simulation et non d'une prédiction.

## 9. Agents et orchestration

Chaque parcours est un graphe LangGraph. Les agents en sont les nœuds, les validations de January sont des interruptions, et chaque événement est diffusé à l'interface puis enregistré.

### 9.1 Les 17 agents

| Agent | Rôle | Features | Niveau de modèle |
| --- | --- | --- | --- |
| Modérateur | Ordonne les tours, pose les questions de cadrage, résume | F1, F19 | Rapide |
| Stratège | Architecte du parcours, des prérequis et du planning | F1, F2, F13, F15 | Fort |
| Praticien | Voix du terrain : ce qui sert vraiment dans le métier, projets | F1, F11 | Standard |
| Éclaireur | Recherche web, tri des sources, repère de vrais praticiens | F1, F2, F12, F16, F17 | Rapide |
| Sceptique | Conteste, vérifie la faisabilité face au budget temps, coupe le superflu | F1 | Standard |
| Scribe | Dessine au tableau, tient le compte rendu | F1, F14 | Rapide |
| Rédacteur | Écrit les leçons | F2 | Fort |
| Vérificateur | Contrôle les faits, les liens et l'originalité | F2, F16 | Standard |
| Archiviste | Ingestion, extraction de concepts, profil maître | F3, F4, F18 | Rapide |
| Lecteur ATS | Lecture machine du CV | F4, F19 | Standard |
| Recruteur | Lecture humaine du CV | F4, F19 | Standard |
| Maquettiste | Reproduit le design du CV, nécessite la vision | F4 | Vision |
| Analyste | Extraction de compétences, scores de match | F8, F12 | Rapide |
| Examinateur | Quiz, notation, fiches de révision | F9 | Standard |
| Intervieweur | Entretiens blancs et débriefs | F10 | Fort |
| Tuteur | Accompagne les sessions d'étude | F14 | Standard |
| Assistant de suivi | Fiches candidatures en langage naturel, brouillons de messages | F5, F16 | Rapide |

Les quatre agents qui débattent dans le conseil d'apprentissage sont le Stratège, le Praticien, l'Éclaireur et le Sceptique. Le Modérateur et le Scribe les servent sans prendre position.

Le comité de recrutement (F19) réutilise le Lecteur ATS et le Recruteur, et ajoute deux personas, le Manager et le Futur collègue, définis comme des variantes de prompt du Recruteur.

### 9.2 Un graphe par parcours

Seize graphes, un module chacun : `learning_council`, `program_builder`, `lesson_factory`, `cv_capture`, `cv_review`, `application_kit`, `gap_analysis`, `quiz`, `interview`, `market_radar`, `replan`, `study_session`, `capture`, `hiring_committee`, `daily_brief`, `project_review`.

Tous suivent le même squelette : charger le contexte mémoire, travailler, s'arrêter pour validation, finaliser, écrire en mémoire.

### 9.3 Règles du débat

- Le Modérateur fixe l'ordre de parole. Chaque agent voit tous les tours précédents.
- 150 mots au maximum par prise de parole.
- Toute affirmation sur le domaine cite une source récupérée ou un élément de la mémoire.
- À partir du tour 2, chaque agent répond nommément à au moins un autre.
- Le Sceptique formule au moins une objection par tour.
- Les messages de January sont traités en priorité au tour suivant.
- Le Modérateur arrête le débat plus tôt si les positions ne bougent plus.
- Un plafond de tokens par session est réglable, et le coût estimé s'affiche en direct.

### 9.4 Humain dans la boucle

- Les points d'arrêt utilisent `interrupt()` de LangGraph avec une charge JSON : type, question, options ([documentation](https://docs.langchain.com/oss/python/langgraph/interrupts)).
- Il faut un checkpointer et un `thread_id`. Le `thread_id` est l'identifiant de session. La reprise se fait avec `Command(resume=valeur)`.
- Checkpointer : SQLite asynchrone, dans un fichier `checkpoints.db` séparé de la base métier.
- **Piège à respecter.** À la reprise, le nœud interrompu redémarre depuis son début. Aucun effet de bord (écriture en base, appel payant) ne doit précéder `interrupt()` dans le même nœud.

### 9.5 Événements temps réel

Chaque exécution publie des événements typés, enregistrés dans `session_events` puis poussés par WebSocket.

| Type | Contenu |
| --- | --- |
| `agent.started` | Agent, étape, phrase d'intention (« je cherche des cursus reconnus ») |
| `agent.token` | Fragment de texte en cours d'écriture |
| `agent.message` | Message final de l'agent |
| `tool.called`, `tool.result` | Outil, arguments, résumé du résultat |
| `source.found` | Titre, lien, auteur, date, langue, score |
| `board.update` | Code Mermaid et numéro d'étape |
| `memory.written` | Élément écrit et raison |
| `interrupt.requested` | Question et options pour January |
| `proposal.ready`, `artifact.ready` | Proposition ou fichier prêt (PDF, plan) |
| `cost.updated` | Tokens et coût estimé cumulés |
| `run.completed`, `run.failed` | Fin, avec résumé ou erreur |

- Enveloppe commune : `id`, `session_id`, `seq`, `ts`, `type`, `agent`, `payload`.
- À la reconnexion, le client envoie son dernier `seq` et le serveur rejoue la suite.
- La « pensée » affichée est la phrase d'intention et les appels d'outils de chaque étape, pas un raisonnement brut.

### 9.6 Fiabilité

- Toute sortie structurée (propositions, plan, modifications de CV, quiz) passe par un schéma Pydantic. Deux nouveaux essais en cas d'échec de validation, puis un événement d'erreur lisible.
- Délai maximal de 120 secondes par nœud, nouveaux essais avec attente croissante sur les erreurs du fournisseur.
- Un prompt par agent, dans un fichier Markdown versionné, avec variables.
- Chaque appel LLM est journalisé dans `llm_calls` : modèle, tokens, latence, coût estimé. Un écran Journal des agents les affiche.
- Tâches planifiées par APScheduler dans le processus du back end : brief, radar, bilan hebdomadaire, relances, leçons à 7 jours, rafraîchissement des connaissances ATS.

## 10. Recherche web gratuite

La recherche passe par SearXNG, un métamoteur open source lancé dans Docker : gratuit, sans clé et sans quota. Brave Search n'a plus de plan gratuit sans carte bancaire, il reste donc une option de secours.

### 10.1 Fournisseurs

| Fournisseur | Coût | Clé API | Rôle |
| --- | --- | --- | --- |
| SearXNG, conteneur local | Gratuit, open source | Aucune | Par défaut |
| Brave Search API | 5 $ de crédit par mois, soit environ 1 000 requêtes, carte bancaire exigée | Oui | Optionnel, activé seulement si une clé est saisie |

- Le code dépend d'une interface `SearchProvider` : `search(query, lang, time_range, categories)` renvoie une liste de résultats (titre, lien, extrait, moteur, date).
- L'ordre de repli est réglable. Par défaut : SearXNG, puis Brave si une clé existe.
- SearXNG doit avoir le format JSON activé dans `settings.yml` (`search.formats: [html, json]`). Le fichier est fourni dans le dépôt.
- Moteurs activés : généralistes, plus Wikipedia, GitHub, arXiv, Stack Overflow et YouTube.
- **Risque connu.** Un moteur généraliste peut bloquer temporairement une instance SearXNG trop active. Parades : plusieurs moteurs en parallèle, cache, débit limité.

### 10.2 Lecture des pages

| Type de contenu | Méthode gratuite |
| --- | --- |
| Page web | Téléchargement avec `httpx`, extraction du texte principal avec `trafilatura` |
| Page rendue en JavaScript | Repli : conversion de l'adresse en PDF par Gotenberg, puis extraction du texte |
| PDF | Téléchargement et extraction de texte |
| Vidéo YouTube | Transcription quand elle est disponible, sinon titre et description |
| Dépôt GitHub | API publique, lecture du README |
| Papier de recherche | API arXiv |

- L'outil `web_read(url)` renvoie texte, titre, auteur, date, langue, et un statut `ok` ou `unreadable`.
- Une page `unreadable` n'est jamais citée. Aucun contournement de page protégée par connexion.
- Chaque page lue est mise en cache 7 jours dans `web_cache`.
- Délai maximal de 15 secondes par page, une requête par seconde et par domaine.

### 10.3 Qualité des sources

L'Éclaireur note chaque source sur 100. Il faut 60 pour entrer dans une leçon.

| Critère | Points |
| --- | --- |
| Autorité : documentation officielle, institution reconnue, praticien au rôle vérifiable | 30 |
| Fraîcheur : date de publication, moins de 12 mois privilégié pour les sujets IA | 20 |
| Profondeur du contenu | 20 |
| Auteur réel et identifiable | 15 |
| Qualité pédagogique | 15 |

- **Vraies personnes.** Pour chaque objectif, l'Éclaireur repère 5 à 10 praticiens (nom, rôle, où ils publient). Leurs articles et conférences sont prioritaires. Seules des informations professionnelles publiques sont conservées.
- **Langues.** Requêtes en français et en anglais par défaut, autres langues activables. La leçon résume en français et cite la source dans sa langue.
- Listes de domaines privilégiés et exclus, modifiables dans les réglages.
- L'interface montre les requêtes lancées, les sources retenues et les sources écartées avec la raison.

### 10.4 Plafonds

- 12 requêtes et 30 pages lues par session, réglables.
- Sur Cloudflare, SearXNG ne pourra pas tourner dans un Worker. Le choix se fera à la migration : crédit mensuel Brave, ou SearXNG hébergé ailleurs.

## 11. Configuration des modèles et des clés (F6)

L'écran Réglages permet de choisir le fournisseur et le modèle par niveau, et de saisir les clés API. Une seule clé LLM suffit pour faire tourner toute l'application.

### 11.1 Fournisseurs

| Fournisseur | Intégration | Variable | Remarque |
| --- | --- | --- | --- |
| Anthropic | `langchain-anthropic`, classe `ChatAnthropic` | `ANTHROPIC_API_KEY` | Fournisseur par défaut |
| OpenAI | `langchain-openai`, classe `ChatOpenAI` | `OPENAI_API_KEY` |  |
| GLM (Z.ai) | `ChatOpenAI` avec `base_url` | `ZAI_API_KEY` | API compatible OpenAI. Adresse par défaut `https://api.z.ai/api/paas/v4/`, modifiable car elle diffère selon l'offre souscrite |

Une fabrique unique, `get_chat_model(tier)`, construit le bon client. Aucun agent n'instancie un modèle lui même.

### 11.2 Niveaux de modèle

Les agents ne nomment jamais un modèle. Ils demandent un niveau, et les réglages associent chaque niveau à un fournisseur et un modèle.

| Niveau | Usage | Défaut au premier lancement |
| --- | --- | --- |
| `rapide` | Recherche, extraction, modération | Claude Haiku |
| `standard` | Débat, relecture, quiz, tutorat | Claude Haiku |
| `fort` | Planning, rédaction des leçons, entretiens | Claude Haiku |
| `vision` | Capture du design du CV | Claude Haiku |

- **Préréglages en un clic.** Tout Haiku, Haiku avec Sonnet pour le niveau fort, Tout GLM, Tout OpenAI, Personnalisé.
- La liste des modèles disponibles est chargée depuis l'API de chaque fournisseur quand elle existe. Sinon, saisie libre de l'identifiant.
- Identifiants par défaut regroupés dans un seul fichier `model_defaults.py` : `claude-haiku-5-5` et `claude-sonnet-5-5`, à revérifier dans la documentation Anthropic au moment de coder.
- Mode avancé : surcharge du modèle agent par agent.
- Si le niveau `vision` pointe vers un modèle sans vision, la capture du design est désactivée avec un message clair.

### 11.3 Clés API

- Deux façons de les fournir : le fichier `.env` à la racine, ou l'écran Réglages.
- Une clé saisie dans l'interface est chiffrée en base avec `APP_SECRET`, généré automatiquement au premier démarrage dans un volume Docker.
- Une clé n'est jamais renvoyée au navigateur (seuls les 4 derniers caractères s'affichent) ni écrite dans les journaux.
- Le bouton « Tester » fait un appel minimal et affiche le résultat.
- Les embeddings et la recherche web ne demandent aucune clé.
- La clé Brave est optionnelle. Si elle est saisie, l'application s'arrête à 900 requêtes par mois, car Brave facture au delà du crédit.

### 11.4 Autres réglages

| Réglage | Défaut |
| --- | --- |
| Disponibilité | 2 h du lundi au vendredi, 3 à 4 h le week end |
| Langue des leçons | Français |
| Langues de recherche | Français, anglais |
| Tours de débat | 3 |
| Plafond par session | 300 000 tokens |
| Heure du brief | 7 h |
| Bilan hebdomadaire | Dimanche 18 h |
| Délais de relance | 7, 14 et 21 jours |
| Guide de style personnel | Vide |
| Domaines privilégiés et exclus | Liste de départ fournie |

### 11.5 Suivi des coûts

Un écran affiche les tokens et le coût estimé par jour, par feature, par agent et par modèle. Les prix viennent d'un fichier `model_prices.json` modifiable, car ils changent.

## 12. Architecture technique et structure du code

Six conteneurs Docker : le front, le back end, et quatre services open source que le back end appelle à travers des interfaces. Ces interfaces sont ce qui rendra la migration vers Cloudflare possible sans réécrire les features.

&#91;embedded content: architecture · 6 conteneurs, 2 dépendances externes\]

Seule la boîte Interfaces providers connaît les services. C'est elle que l'on réécrit pour passer sur Cloudflare.

### 12.1 Stack

| Couche | Choix | Raison |
| --- | --- | --- |
| Back end | Python, FastAPI, Uvicorn | Asynchrone, WebSocket natif, FastAPI est supporté par Python Workers |
| Agents | LangChain et LangGraph | Demande explicite, interruptions et reprises intégrées |
| Schémas | Pydantic v2 | Sorties structurées et validation de l'API |
| Base relationnelle | SQLite en mode WAL, SQLAlchemy 2 asynchrone, Alembic | Aucun conteneur en plus, schéma proche de Cloudflare D1 |
| Base vectorielle | Qdrant | Section 4 |
| Embeddings | Ollama avec `bge-m3` | Local, gratuit, multilingue |
| Recherche web | SearXNG | Section 10 |
| Génération de PDF | [Gotenberg](https://github.com/gotenberg/gotenberg) (Chromium) | HTML vers PDF fidèle au CSS, pour les leçons et les CV |
| Lecture de PDF | `pdfplumber`, `pypdfium2` | Texte avec positions, images de pages |
| Lecture du web | `httpx`, `trafilatura` | Extraction du contenu principal |
| Tâches planifiées | APScheduler | Dans le processus, sans file externe |
| Fichiers | Volume Docker derrière une interface `FileStorage` | Remplaçable par R2 |
| Front end | React, TypeScript, Vite | Standard, rapide |
| Interface | Tailwind CSS, shadcn/ui | Thème clair uniquement |
| Données côté front | TanStack Query, Zustand | Cache serveur et état local |
| Tableau | Excalidraw et `@excalidraw/mermaid-to-excalidraw` | Rendu dessiné à la main, éditable |
| Carte de compétences | React Flow avec `elkjs` | Graphe structuré avec mise en page automatique |
| Graphiques | Recharts | Radar, courbes, barres |
| Tests | pytest, Vitest, Playwright | Unitaires, composants, 3 parcours de bout en bout |
| Qualité | ruff, mypy, ESLint, Prettier | Contrôles avant chaque commit |

Les versions sont les dernières stables au moment de coder, figées dans les fichiers de verrouillage.

### 12.2 Règles de découpage

- **300 lignes au maximum par fichier**, 50 par fonction. Contrôlé par ESLint (`max-lines`) côté front et par un script `scripts/check_file_length.py` côté back, tous deux bloquants en pre commit.
- **Un dossier par feature**, des deux côtés, avec les mêmes noms.
- **Trois couches côté back.** Le routeur reçoit et répond, le service porte la logique, le repository parle à la base. Un routeur n'appelle jamais la base.
- **Tout service externe passe par une interface** dans `providers/` : LLM, recherche, embeddings, vecteurs, PDF, fichiers. Les features ne connaissent que l'interface.
- **Un agent, deux fichiers** : son prompt en Markdown et son nœud en Python. Un graphe, un fichier.
- Les types TypeScript de l'API sont générés depuis le schéma OpenAPI du back end, jamais écrits à la main.

### 12.3 Arborescence du back end

```text
backend/
  pyproject.toml
  Dockerfile
  alembic/
  scripts/check_file_length.py
  app/
    main.py              # création de l'app, montage des routeurs
    config.py            # réglages lus depuis l'environnement
    core/                # sécurité, chiffrement, erreurs, journalisation
    db/                  # moteur, session, modèles (un fichier par groupe de tables)
    providers/
      llm/               # factory.py, anthropic.py, openai.py, glm.py
      search/            # base.py, searxng.py, brave.py
      embeddings/        # base.py, ollama.py
      vector/            # base.py, qdrant.py
      pdf/               # base.py, gotenberg.py, extract.py
      storage/           # base.py, local.py
      web/               # reader.py, youtube.py, github.py, arxiv.py
    agents/
      prompts/           # un fichier .md par agent (17)
      nodes/             # un fichier .py par agent (17)
      graphs/            # un fichier par graphe (16)
      state/             # schéma d'état de chaque graphe
      tools/             # memory_tools.py, web_tools.py, board_tools.py
      runtime/           # runner.py, checkpointer.py, events.py, costs.py
    features/            # chaque dossier : router, service, repository, schemas
      learning/  program/  lessons/  memory/  cv/  applications/
      gap/  quiz/  interview/  projects/  radar/  replan/
      study/  skills/  kit/  brief/  capture/  committee/
      settings/  auth/
    realtime/            # websocket.py, replay.py
    scheduler/           # un fichier par tâche planifiée
    templates/           # gabarits HTML et CSS : lesson, program, report, cv
  tests/
```

### 12.4 Arborescence du front end

```text
frontend/
  package.json
  Dockerfile
  vite.config.ts
  src/
    main.tsx
    app/                 # routes, layout, providers
    shared/
      api/               # client HTTP, types générés depuis OpenAPI
      realtime/          # useSessionStream, rejeu des événements
      ui/                # composants shadcn
      i18n/              # fr.ts
      lib/
    features/            # chaque dossier : components, hooks, api.ts, types.ts
      home/              # brief du matin
      learning/          # DebatePanel, AgentBubble, SourcesPanel, Board, ProposalCards
      program/           # WeekCalendar, TaskList, PlanDiff
      lessons/  study/  quiz/
      memory/            # liste, carte 2D, banc d'essai
      skills/            # carte de compétences
      cv/                # profil maître, capture du design, revue, diff
      applications/      # kanban, fiche, relances
      kit/  committee/  interview/  radar/  projects/
      capture/  settings/  auth/
```

## 13. Modèle de données

La base SQLite porte toutes les données métier et le texte source de la mémoire. Qdrant ne contient que les vecteurs et une copie du payload.

### 13.1 Règles communes

- Chaque table a `id` (UUID en texte), `user_id`, `created_at`, `updated_at`. Dates en UTC au format ISO.
- Toute requête d'un repository filtre par `user_id`, même en mode local à un seul utilisateur.
- Types limités à ceux de SQLite, données souples en colonnes JSON, pour rester compatible avec D1.
- Le schéma n'évolue que par migrations Alembic.
- Les fichiers vivent dans `storage/<user_id>/<type>/`. La base ne stocke que leur chemin.

### 13.2 Comptes et agents

| Table | Contenu |
| --- | --- |
| `users` | Email, nom, identifiant Google, langue |
| `user_settings` | Disponibilité, langues, niveaux de modèle, guide de style, horaires des tâches |
| `api_keys` | Fournisseur, clé chiffrée, 4 derniers caractères, date du dernier test |
| `sessions` | Graphe exécuté, statut (`running`, `waiting_user`, `completed`, `failed`), objet lié, tokens, coût |
| `session_events` | Session, `seq`, type, agent, payload, horodatage |
| `llm_calls` | Session, agent, fournisseur, modèle, tokens entrants et sortants, latence, coût |
| `jobs` | Tâche planifiée, dernier passage, prochain passage, erreur |

### 13.3 Apprentissage

| Table | Contenu |
| --- | --- |
| `goals` | Objectif, poste cible, échéance, statut |
| `proposals` | Parcours proposés pour un objectif, celui qui a été choisi |
| `boards` | États successifs du tableau : code Mermaid, scène Excalidraw |
| `programs` | Objectif, version, statut, date de début, heures par semaine |
| `weeks` | Rang, thème, objectif, charge, livrable |
| `modules` | Semaine, titre, compétences visées, leçon liée |
| `tasks` | Module, titre, type, durée, critère de fin, jour planifié, statut |
| `lessons` | Module, Markdown, chemin du PDF, statut, nombre de mots |
| `resources` | Module, type, titre, lien, auteur, date, langue, durée, niveau, raison, score, copie locale |
| `sources` | Pages et personnes repérées : lien, auteur, langue, date, score, résumé |
| `plan_versions` | Version du programme, diff, raison, date d'acceptation |
| `study_sessions` | Début, fin, minutes, mode, résumé |
| `quizzes`, `quiz_questions`, `quiz_attempts` | Quiz par module, questions, tentatives et notes |
| `flashcards` | Recto, verso, compétence, intervalle, date d'échéance |
| `projects` | Brief, lien du rendu, statut, évaluation, brouillons générés |
| `journal_entries` | Type, texte, liens vers session, capture ou quiz |

### 13.4 Compétences et mémoire

| Table | Contenu |
| --- | --- |
| `skills` | Nom, domaine, synonymes |
| `skill_edges` | Lien de prérequis entre deux compétences |
| `user_skills` | Niveau de maîtrise et preuves, par compétence |
| `skill_snapshots` | Relevé hebdomadaire des niveaux, pour la courbe de progression |
| `documents` | Fichier importé : nom, type, chemin, statut, hash |
| `memory_items` | Élément de mémoire : `kind`, titre, texte, tags, auteur, hash |
| `memory_chunks` | Fragment d'un élément, avec l'identifiant du vecteur dans Qdrant |
| `memory_writes` | Journal des écritures : agent, session, raison |

### 13.5 Carrière

| Table | Contenu |
| --- | --- |
| `master_profile` | Profil maître en JSON, versionné |
| `cv_templates` | Template HTML et CSS, polices, score de ressemblance, statut |
| `job_postings` | Lien, lien normalisé, entreprise, intitulé, texte figé, analyse structurée |
| `companies` | Nom normalisé, dossier entreprise, sources, date de rafraîchissement |
| `cv_reviews` | Offre, session, indicateurs avant et après |
| `cv_modifications` | Section, avant, après, raison, type, faits du profil cités, statut |
| `cv_versions` | Offre, template, contenu JSON, chemin du PDF |
| `applications` | Offre, statut, date, canal, version du CV, prochaine action |
| `application_events` | Historique daté d'une candidature |
| `contacts` | Nom, rôle, lien, candidature liée |
| `reminders` | Type, échéance, statut, brouillon |
| `kit_items` | Pièce du kit : type, contenu, statut |
| `interviews` | Mode, durée, échanges, débrief |
| `committee_runs` | Version du CV, offre, votes, verdict |
| `radar_runs` | Poste, zone, offres lues, offres bloquées, classement des compétences |

### 13.6 Système

| Table | Contenu |
| --- | --- |
| `briefs` | Brief du jour en JSON |
| `web_cache` | Page lue : hash du lien, contenu, date |

**Index à créer dès la première migration** : `session_events(session_id, seq)`, `tasks(planned_date)`, `flashcards(due_date)`, `job_postings(url_norm)`, `job_postings(company_norm, title)`, `reminders(due_at, status)`.

## 14. API

L'API REST vit sous `/api/v1`. Tout parcours long suit le même contrat : un POST crée une session, un WebSocket diffuse ses événements, un POST répond aux interruptions.

### 14.1 Contrat des sessions d'agents

| Méthode | Chemin | Rôle |
| --- | --- | --- |
| POST | `/sessions` | Lance un graphe : `{graph, input}`. Renvoie `session_id` en moins de 2 secondes |
| GET | `/sessions/{id}` | État, dernier `seq`, interruption en attente |
| WS | `/sessions/{id}/stream?after_seq=N` | Flux des événements de la section 9.5, avec rejeu |
| POST | `/sessions/{id}/resume` | Répond à une interruption : `{interrupt_id, value}` |
| POST | `/sessions/{id}/message` | Message de January pendant un débat |
| POST | `/sessions/{id}/pause`, `/cancel` | Met en pause ou annule |
| GET | `/sessions?graph=&status=` | Historique |

Le WebSocket ne transporte que des événements du serveur vers le client. Toute action de January passe par REST, pour être journalisée.

### 14.2 Endpoints par domaine

| Domaine | Endpoints |
| --- | --- |
| Objectifs et programme | `GET POST /goals`, `GET /goals/{id}/proposals`, `POST /proposals/{id}/choose`, `GET PATCH /programs/{id}`, `POST /programs/{id}/validate`, `GET /programs/{id}/export.pdf`, `GET /programs/{id}/export.ics`, `PATCH /tasks/{id}` |
| Leçons et ressources | `GET /lessons/{id}`, `GET /lessons/{id}/pdf`, `GET /resources`, `PATCH /resources/{id}` |
| Étude | `POST PATCH /study-sessions`, `GET /flashcards/due`, `POST /flashcards/{id}/review`, `GET /quizzes/{id}`, `POST /quizzes/{id}/attempts` |
| Mémoire | `POST GET /documents`, `GET POST PATCH DELETE /memory/items`, `POST /memory/search`, `GET /memory/map`, `GET /memory/stats`, `POST /memory/reindex`, `GET /memory/export`, `POST /capture` |
| Compétences | `GET /skills/graph`, `GET /skills/{id}`, `GET /skills/compare`, `GET /skills/history` |
| Profil et CV | `GET PUT /profile`, `GET POST /cv/templates`, `POST /cv/reviews`, `PATCH /cv/modifications/{id}`, `POST /cv/reviews/{id}/generate`, `GET /cv/versions/{id}/pdf` |
| Offres | `POST /postings` (lien ou texte, renvoie aussi le résultat du contrôle doublon), `GET /postings/{id}`, `GET /postings/{id}/gap` |
| Candidatures | `GET POST PATCH /applications`, `POST /applications/{id}/events`, `GET /reminders`, `PATCH /reminders/{id}`, `POST GET /applications/{id}/kit`, `GET /applications/{id}/kit.zip`, `POST /applications/{id}/interviews`, `POST /committee` |
| Radar et projets | `POST /radar/runs`, `GET /radar/latest`, `GET /projects`, `POST /projects/{id}/submit` |
| Accueil | `GET /brief/today`, `GET /activity`, `GET /journal` |
| Réglages | `GET PUT /settings`, `GET POST DELETE /settings/api-keys`, `POST /settings/api-keys/{provider}/test`, `GET /settings/models`, `GET /costs` |
| Connexion | `GET /auth/google/login`, `GET /auth/google/callback`, `POST /auth/logout`, `GET /auth/me` |
| Santé | `GET /health` : état de la base, de Qdrant, d'Ollama, de SearXNG, de Gotenberg et de chaque fournisseur LLM |

### 14.3 Conventions

- JSON en `snake_case`, documentation OpenAPI servie sur `/api/docs`.
- Erreurs au format `{error: {code, message, details}}`, avec un message lisible en français.
- Aucune requête HTTP n'attend la fin d'un travail d'agent. Elle renvoie un `session_id`.
- `POST /postings` est idempotent sur le lien normalisé.

## 15. Front end

Une application d'une page en thème clair, avec une navigation latérale de 8 entrées et un champ de capture global.

### 15.1 Navigation

| Entrée | Écrans |
| --- | --- |
| Accueil | Brief du matin, actions rapides, fil d'activité |
| Apprendre | Objectifs, Conseil, Programme, Leçons, Bibliothèque |
| Étudier | Session guidée, Révisions, Quiz |
| Compétences | Carte, radar, progression, Portfolio |
| Carrière | Profil maître, CV (templates, revues, versions), Offres et écarts, Radar |
| Candidatures | Kanban, fiche, relances, kit, entretiens, comité |
| Mémoire | Explorateur, carte 2D, banc d'essai, documents |
| Réglages | Modèles et clés, disponibilité, style, coûts, journal des agents |

### 15.2 Écran Conseil

C'est l'écran vitrine. Il sert aussi au comité de recrutement (F19) avec les mêmes composants.

- **Barre d'état en haut.** Étape en cours (Cadrage, Recherche, Débat, Propositions, Programme), tour en cours, tokens et coût estimé.
- **Colonne gauche, 40 % de la largeur.** Le fil du débat. Une bulle par agent avec avatar, nom, rôle et couleur propre. Le texte s'écrit au fil de l'eau.
- Chaque bulle montre l'activité de l'agent (réfléchit, cherche, écrit) et ses appels d'outils en pastilles dépliables.
- Les citations sont des pastilles numérotées qui ouvrent la source.
- **Zone droite, 60 %.** Trois onglets : Tableau, Sources, Propositions.
- **Bas de page.** Champ de message et boutons Pause, Relancer un tour, Passer aux propositions.
- Une interruption s'affiche comme une carte dans le fil, avec la question et ses options. Jamais de boîte de dialogue bloquante du navigateur.
- Les propositions sont des cartes comparables côte à côte : Choisir, Mélanger, Demander un autre tour.

### 15.3 Composants clés par écran

| Écran | Composants |
| --- | --- |
| Programme | `WeekCalendar` avec glisser déposer entre les jours, `TaskList`, `PlanDiff` avant et après |
| Leçon | Lecteur avec sommaire, progression, « Demander au tuteur » sur un passage sélectionné, téléchargement PDF |
| CV | `MasterProfileForm`, `TemplateCompare` (original et rendu avec curseur), `ReviewDiff` (accepter ou refuser), jauges avant et après, aperçu PDF |
| Candidatures | Kanban, tiroir de fiche, `ReminderCard` avec bouton Copier, `DuplicateAlert` |
| Mémoire | Table filtrable, `VectorMap` (nuage de points zoomable), `SearchBench` |
| Compétences | `SkillGraph`, `SkillRadar`, `ProgressChart` |
| Partout | `CommandCapture` (Cmd K), `ActivityFeed`, pastille de coût, voyant de santé des services |

### 15.4 Design

- Thème clair uniquement : fond blanc cassé, texte anthracite, une couleur d'accent, pas de mode sombre.
- Une couleur fixe par agent, reprise dans les bulles, les annotations du tableau et les journaux.
- Colonne de lecture des leçons limitée à 72 caractères, corps de 18 px.
- Animations de moins de 300 ms, désactivées si `prefers-reduced-motion` est actif.
- Contraste AA, navigation au clavier, focus visible, zones de texte en cours d'écriture annoncées aux lecteurs d'écran.
- Conçu pour un écran de 1 280 px et plus, utilisable à 1 024 px.
- Chaque écran a un état vide avec une action proposée, un état de chargement et un état d'erreur avec nouvel essai.
- Une notification discrète signale le travail de fond (« Leçon 3 prête »).

### 15.5 Premier lancement

1. Contrôle de santé des services, avec la progression du téléchargement du modèle d'embedding.
2. Saisie et test d'une clé API.
3. Import du CV et de l'export LinkedIn (peut être passé).
4. Réglage de la disponibilité.
5. Premier objectif, qui lance le Conseil.

## 16. Docker en local, puis Cloudflare

Une commande, `docker compose up`, lance toute la plateforme. Chaque service local a un équivalent Cloudflare identifié, mais la migration comporte des points non vérifiés, listés en 16.4.

### 16.1 Services

| Service | Image | Accès | Rôle |
| --- | --- | --- | --- |
| `frontend` | Construite depuis `./frontend` | `http://localhost:5173` | Interface |
| `backend` | Construite depuis `./backend` | `http://localhost:8000` | API, agents, tâches planifiées |
| `qdrant` | `qdrant/qdrant` | `http://localhost:6333/dashboard` | Vecteurs et tableau de bord |
| `ollama` | `ollama/ollama` | Réseau interne | Embeddings |
| `ollama-init` | `ollama/ollama` | S'arrête après usage | Télécharge `bge-m3` au premier démarrage |
| `searxng` | `searxng/searxng` | Réseau interne | Recherche web |
| `gotenberg` | `gotenberg/gotenberg:8` | Réseau interne | HTML vers PDF |

- Volumes nommés : `app_data` (SQLite, checkpoints, fichiers, secret), `qdrant_data`, `ollama_data`.
- Le back end attend que les quatre services répondent avant de se déclarer prêt. `GET /health` détaille l'état de chacun.
- Un second fichier, `docker-compose.dev.yml`, ajoute le rechargement à chaud des deux côtés.
- Sur macOS, Docker n'accède pas au GPU. La variable `OLLAMA_BASE_URL` permet de pointer vers un Ollama installé sur la machine.

### 16.2 Racine du dépôt et démarrage

```text
tremplin/
  frontend/
  backend/             # contient aussi infra/searxng/settings.yml
  docker-compose.yml
  docker-compose.dev.yml
  .env.example
  README.md
  SPEC.md              # ce document
```

```bash
cp .env.example .env     # y coller au moins une clé LLM
docker compose up -d
# ouvrir http://localhost:5173
```

```bash
# .env.example : seules les clés sont à remplir
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
ZAI_API_KEY=
BRAVE_API_KEY=            # optionnel
AUTH_MODE=local           # local ou google
GOOGLE_CLIENT_ID=         # requis seulement si AUTH_MODE=google
GOOGLE_CLIENT_SECRET=
```

### 16.3 Correspondance avec Cloudflare

| En local | Sur Cloudflare |
| --- | --- |
| FastAPI dans Docker | [Python Workers](https://developers.cloudflare.com/workers/languages/python/), où FastAPI et LangChain figurent parmi les paquets supportés |
| SQLite | D1 |
| Qdrant | Vectorize |
| Ollama avec `bge-m3` | Workers AI avec `@cf/baai/bge-m3` |
| Volume de fichiers | R2 |
| WebSocket et état des sessions | Durable Objects |
| APScheduler | Cron Triggers |
| Gotenberg | Browser Rendering, ou génération du PDF dans le navigateur |
| SearXNG | Crédit mensuel Brave, ou SearXNG hébergé ailleurs |
| Front servi par le conteneur | Workers Static Assets |

Ce qui rend la migration abordable : les interfaces de `providers/`, un schéma limité aux types SQLite, le texte comme source de vérité de la mémoire, et le même modèle d'embedding des deux côtés.

### 16.4 Points à tester avant de migrer

Aucun de ces points n'a été vérifié. Ils sont à tester dans une phase dédiée, après le MVP local.

1. LangGraph et son checkpointer sur Python Workers. Le code y tourne en WebAssembly, et un paquet qui dépend d'extensions natives peut ne pas s'installer.
2. Le temps CPU par requête du plan gratuit, face au démarrage de Python et à l'import de LangChain.
3. `pdfplumber`, `pypdfium2` et `trafilatura` en WebAssembly. Repli : déplacer la lecture de PDF dans le navigateur.
4. La capacité gratuite de Vectorize, environ 4 880 fragments à 1 024 dimensions.
5. Le quota gratuit quotidien de Workers AI pour les embeddings.
6. La durée des graphes longs (leçons, radar) face aux limites d'une requête.

**Repli global** si Python Workers bloque : garder Cloudflare pour le front, D1, Vectorize et R2, et héberger le conteneur du back end ailleurs.

## 17. Connexion Google, sécurité et confidentialité (F7)

En local, l'application démarre sans page de connexion, avec un utilisateur unique. La connexion Google s'active par une variable d'environnement, sans changement de code.

### 17.1 Deux modes

| Mode | Comportement |
| --- | --- |
| `AUTH_MODE=local` (défaut) | Un utilisateur `local` est créé au premier démarrage. Aucune connexion demandée |
| `AUTH_MODE=google` | Connexion Google en OAuth 2.0 (code d'autorisation avec PKCE), portées `openid email profile`, un espace par utilisateur |

- Session par cookie `HttpOnly` et `SameSite=Lax`, valable 30 jours.
- Adresse de retour : `http://localhost:8000/api/v1/auth/google/callback`.
- Au premier passage en mode Google, le compte qui se connecte peut reprendre les données de l'utilisateur `local`.
- La variable `ALLOWED_EMAILS` limite les comptes autorisés : liste d'adresses séparées par des virgules (minuscules, espaces ignorés) ; `*` laisse entrer tous les comptes ; en mode Google, vide, le back refuse de démarrer. La reprise des données de l'utilisateur `local` n'est proposée qu'à une adresse nommée dans une liste explicite, jamais avec `*`.
- Ce mode demande de créer un client OAuth dans la console Google. C'est la seule configuration au delà des clés API, d'où sa désactivation par défaut. Le README décrit les étapes.

### 17.2 Isolation et secrets

- `user_id` sur chaque ligne, filtre `user_id` dans Qdrant, dossier de fichiers par utilisateur.
- Un test par routeur vérifie qu'un utilisateur ne lit jamais les données d'un autre.
- Clés API chiffrées en base, jamais journalisées, jamais renvoyées au navigateur.
- Les journaux citent des identifiants, pas le contenu des CV ni des documents.

### 17.3 Ce qui sort de la machine

| Donnée | Destination |
| --- | --- |
| Prompts, qui peuvent contenir le CV et le profil | Le fournisseur LLM choisi |
| Requêtes de recherche | Les moteurs interrogés par SearXNG |
| Tout le reste (base, vecteurs, fichiers, embeddings) | Reste en local |

- L'écran de premier lancement l'explique en clair.
- L'outil de recherche retire nom, email et téléphone des requêtes avant envoi.
- Les contacts enregistrés se limitent au nom, au rôle et à un lien public.
- Deux boutons dans les réglages : Exporter toutes mes données, Tout supprimer.

### 17.4 Sécurité applicative

- **Contenu non fiable.** Les pages web et les documents importés sont traités comme des données. Les prompts les encadrent par des délimiteurs et interdisent de suivre une instruction trouvée dedans.
- Les agents n'ont que les outils de la section 9 : pas d'accès au système de fichiers ni à un terminal.
- Le lecteur de pages refuse les adresses privées et tout protocole autre que HTTP et HTTPS.
- Le HTML envoyé à Gotenberg est nettoyé de tout script.
- Import de fichiers limité à 20 Mo, avec une liste de types autorisés.
- CORS limité à l'origine du front.
- L'application n'envoie jamais de candidature ni de message à la place de January.

## 18. Plan de construction et critères d'acceptation

Les 19 features sont dans le MVP, construites en 10 phases. Chaque phase se termine par une application qui démarre et un contrôle précis.

### 18.1 Phases

| Phase | Contenu | Terminée quand |
| --- | --- | --- |
| 0. Socle | Dépôt, Docker Compose, santé des services, SQLite et Alembic, réglages, clés API, fabrique LLM pour les 3 fournisseurs, contrôles de qualité | `docker compose up` donne `/health` au vert, et le test de clé réussit depuis les Réglages |
| 1. Moteur d'agents | Exécution LangGraph, checkpointer, bus d'événements, WebSocket avec rejeu, interruptions, journal des coûts, graphe de démonstration à 2 agents | Le débat de démonstration s'affiche en direct, s'arrête sur une question, et reprend après un redémarrage du back end |
| 2. Mémoire (F3) | Embeddings, Qdrant, ingestion, outils mémoire, explorateur | Un PDF importé se retrouve par recherche, et une écriture d'agent s'affiche avec son auteur |
| 3. Recherche web | SearXNG, lecteur de pages, cache, notation des sources | Une requête renvoie des sources notées et lues, et une page illisible est signalée |
| 4. Conseil et programme (F1, F2) | Graphe du conseil, tableau, propositions, programme, calendrier, leçons, PDF, ressources | Un objectif mène à un programme validé avec les leçons PDF de 2 semaines |
| 5. Étude (F9, F13, F14, F15, F18) | Quiz, fiches, session guidée, carte de compétences, replanification, capture, journal | Une session guidée complète met à jour la carte et le planning |
| 6. CV (F4, F8) | Profil maître, capture du design, revue, génération, analyse d'écart | Une offre collée donne un CV ciblé en PDF dans le design d'origine |
| 7. Candidatures (F5, F10, F16, F19) | Suivi, relances, alerte doublon, kit, comité, entretien | Le cycle complet d'une candidature fonctionne, alerte doublon comprise |
| 8. Quotidien (F11, F12, F17) | Radar, brief, projets preuves, fil d'activité, tâches planifiées | Le brief du jour se génère seul et reprend toutes les rubriques |
| 9. Finitions (F6 avancé, F7) | Connexion Google, export et suppression, premier lancement, tests de bout en bout, README | Les 3 parcours de bout en bout passent |

### 18.2 Consignes pour Claude Code

- Lire toute la spec avant de coder, puis avancer phase par phase. À la fin de chaque phase : tests, contrôle de la phase, commit.
- Ne rien ajouter hors spec.
- Si une bibliothèque se comporte autrement que décrit ici, suivre sa documentation officielle actuelle et noter l'écart dans `DECISIONS.md`.
- À vérifier dans la documentation au moment de coder : identifiants de modèles, API de streaming de LangGraph, API des paquets Excalidraw, routes de Gotenberg, adresse de l'API Z.ai.
- Respecter les règles de découpage de la section 12.2 dès le premier fichier.
- Tests écrits avec chaque feature : unitaires sur les services, un test d'API par routeur, 3 parcours de bout en bout (conseil complet, revue de CV complète, cycle de candidature avec doublon et relance).
- Dans les tests, les appels LLM passent par un faux fournisseur déterministe. Aucun test ne dépense de tokens.

### 18.3 Critères d'acceptation par feature

| Feature | Acceptée quand |
| --- | --- |
| F1 | Un objectif produit un débat visible de 4 agents sur 3 tours, au moins 8 sources notées, un tableau qui se dessine, et 2 à 3 propositions. Un message envoyé pendant le débat est repris au tour suivant |
| F2 | Chaque semaine a thème, objectif, livrable et tâches datées, sans dépasser 85 % du budget. Chaque module des 2 premières semaines a sa leçon PDF et 3 à 6 ressources dont les liens répondent |
| F3 | Un PDF importé se retrouve par recherche sémantique. Une écriture d'agent apparaît avec auteur et raison. Un sujet acquis est sauté dans un nouveau programme |
| F4 | Chaque modification a avant, après, raison et fait source. Aucune modification acceptée ne contient un fait absent du profil maître. Le PDF garde son nombre de pages et son texte est sélectionnable |
| F5 | Ajouter une offre déjà postulée déclenche l'alerte avec la date. Une candidature de 7 jours sans réponse fait apparaître une relance avec brouillon |
| F6 | Passer le niveau `fort` d'Anthropic à GLM change le modèle dès la session suivante, visible dans `llm_calls`. Une clé invalide est signalée par le test |
| F7 | En mode Google, deux comptes ne voient jamais les données l'un de l'autre |
| F8 | Une offre produit un score de match et un tableau d'écarts. « Ajouter au planning » crée une proposition de replanification |
| F9 | Un quiz réussi à 80 % fait passer l'acquis à `valide`. Une fiche ratée revient le lendemain |
| F10 | Un entretien de 15 minutes pose des questions liées à l'offre et produit un débrief noté |
| F11 | Un projet validé génère les 4 brouillons et fait passer l'acquis à `prouve` |
| F12 | Le relevé indique les offres lues et bloquées, et classe les compétences par fréquence |
| F13 | Après une semaine à moitié faite, le bilan propose un plan qui respecte le budget, avec l'avant et l'après |
| F14 | Une session guidée enregistre le temps, coche les tâches et crée des fiches depuis les erreurs |
| F15 | La carte reflète un changement de niveau en moins d'une minute et montre les preuves au clic |
| F16 | Le kit produit les 7 pièces, toutes modifiables, et l'archive se télécharge |
| F17 | Le brief du jour existe à l'ouverture et liste bloc, révisions, relances et offres |
| F18 | Un lien capturé devient un élément de mémoire résumé. Un lien illisible est signalé immédiatement |
| F19 | Le comité rend 4 votes motivés et 3 changements prioritaires. Une seconde exécution après modification montre l'écart |

**Critères transverses**

- Avec une seule clé LLM dans `.env`, `docker compose up` suffit. Aucune autre configuration.
- Aucun fichier ne dépasse 300 lignes.
- Une session en cours survit à `docker compose restart backend`.
- Chaque appel LLM est journalisé avec son coût estimé.
- Aucun texte généré au nom de January ne contient un fait absent du profil maître ou de la mémoire.

## 19. Sources

Faits techniques relevés le 11 novembre 2026, à revérifier dans la documentation au moment de coder.

**Pages consultées**

- Tarifs et plan gratuit de Vectorize : [Cloudflare Docs, Vectorize pricing](https://developers.cloudflare.com/vectorize/platform/pricing/)
- Python sur Workers, paquets FastAPI et LangChain : [Cloudflare Docs, Python Workers](https://developers.cloudflare.com/workers/languages/python/)
- Interruptions, checkpointer et reprise dans LangGraph : [LangChain Docs, Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)
- SearXNG avec LangChain et activation du format JSON : [LangChain Docs, SearxNG](https://docs.langchain.com/oss/python/integrations/providers/searx)
- Fin du plan gratuit de Brave Search API : [Implicator](https://www.implicator.ai/brave-drops-free-search-api-tier-puts-all-developers-on-metered-billing/)
- Conversion de Mermaid en éléments Excalidraw : [Excalidraw Docs, mermaid to excalidraw](https://plus.excalidraw.com/docs/mermaid-to-excalidraw/api)
- Fonctionnement réel des logiciels de recrutement : [Huntr](https://huntr.co/blog/how-applicant-tracking-systems-work)

**Repéré par recherche, sans ouvrir la page d'origine**

- Licence Apache 2.0 et tableau de bord intégré de [Qdrant](https://github.com/qdrant/qdrant).
- Routes Chromium de [Gotenberg](https://github.com/gotenberg/gotenberg) pour convertir du HTML en PDF.
- Adresse de l'API Z.ai compatible OpenAI.
- Caractéristiques de `bge-m3` : 1 024 dimensions, plus de 100 langues, disponible dans Ollama et Workers AI.
