# Bilan de la phase 3 (recherche web)

Tag `phase-3`. 11 tâches. Revues par tâche sur Opus high pour les tâches à risque : 3.1, 3.2, 3.3, 3.4 et 3.6. Revue finale en deux parties, back et front, puis une vague de corrections par zone et une re-revue chacune. Tests : back 1 435 passés / 3 ignorés, front 621.

Contrôle de fin de phase sous Docker, avec SearXNG, Gotenberg et GLM 5.3 flash réels :
- SearXNG renvoie 48 résultats de 4 moteurs ; Startpage, bloqué par un captcha, est signalé comme non répondant ;
- Gotenberg refuse `http://qdrant:6333/` et `http://169.254.169.254/` (403), rend `https://example.org/` et convertit toujours du HTML ;
- un `web_research` par l'API (« apprendre asyncio en Python ») trouve 10 sources : 4 retenues (Real Python 89, JetBrains 84, Stéphane Robert 77, bioinfo-fr 69), 5 écartées avec leur raison, 1 illisible (« Page injoignable ») ;
- l'essai dans le navigateur (« bases du machine learning pour débutant » plus l'adresse piégée `http://127.0.0.1:8000/...`) lance 6 requêtes en français et en anglais, retient 3 sources (IBM 91, Stéphane Robert 77, data-bird 62), en écarte 7 et refuse l'adresse piégée sans la lire ; 54 829 tokens, environ 0,03 $ ;
- le journal du back ne contient ni requête ni URL de page.

Brave n'a pas été essayé en réel : aucune clé dans `.env`.

Décisions : D71 à D81 dans `DECISIONS.md`.

## Ce que la phase apporte

- **Recherche :**
  - port `SearchProvider` avec SearXNG (JSON) et Brave (clé chiffrée, 4 derniers caractères seulement côté navigateur, test de clé) ;
  - repli dans l'ordre choisi par l'utilisateur ; Brave plafonné à 900 requêtes par mois UTC par une instruction SQL gardée, cadencé à 1,1 s par clé, réservation rendue quand Brave n'a pas servi ;
  - cache : 7 jours pour une page, 24 h pour une page illisible et pour une liste de résultats ;
  - plafonds de session de 12 requêtes et 30 pages, comptés une seule fois au rejeu.
- **Lecteur étendu :**
  - délai par domaine (1 s, 3 s pour `export.arxiv.org`) dans le budget de 15 s, créneau rendu en cas d'annulation ;
  - lecteurs dédiés pour GitHub (API) et arXiv (Atom, PDF avec échéance interne), repli de rendu par Gotenberg ;
  - Gotenberg durci : adresses privées refusées, `file:` refusé hors `/tmp`, téléchargements coupés ;
  - extraction PDF dans un sous-processus (60 s, 1 Gio, 2 en parallèle, environnement minimal).
- **Données :** tables `web_cache`, `sources`, `web_queries`, `search_usage` ; contenu nettoyé des données personnelles ; `normalize_domain` identique au front.
- **Agents :**
  - port `WebGateway` et outils web ;
  - Éclaireur : note sur 100, seuil 60, raison pour chaque source ;
  - 18e parcours `web_research`, événement `source.found` (statut, verdict, raison, note).
- **Front :**
  - réglages de recherche : langues, domaines préférés et exclus, ordre des fournisseurs, plafonds, compteur Brave ;
  - essai de recherche avec suivi en direct, panneau des sources, pause, reprise et annulation ;
  - « Déjà appris » idempotent et repris après un rechargement (`useRunningLearnings`, `subject_id` dans `SessionView`).

## Arbitrages pris pendant l'exécution

- **Organisation :**
  - le plan a été écrit par un agent Opus sur le code réel de la phase 2, avec les conflits de spec tranchés dedans ;
  - jamais deux implémenteurs back en même temps ; quand deux agents tournent, un seul écrit `DECISIONS.md` et le contrôleur recopie les points de l'autre (D78, D79, corrections de fin de phase) ;
  - la revue de 3.2 a attendu la fin du mode lent du soir ; la session a redémarré et la reprise n'a eu lieu qu'à 5 h.
- **3.2 :** la liste de refus de Gotenberg remplaçait l'exception par défaut pour `/tmp` et cassait `convert/html` ; corrigé avec `(?i)^file:(?!//\/tmp/)`, et WebRTC noté parmi les risques résiduels.
- **3.3 :** deux Minors reportés dans 3.4 (champ `unresponsive_engines` mal formé, corps Brave qui n'est pas un objet), plus un client sans proxy pour le test de clé.
- **3.4 :** le délai par domaine ne rendait jamais un créneau, et un PDF arXiv lent faisait perdre le résumé ; corrigés avec 6 Minors, re-revue sous 600 appels concurrents.
- **3.6 :** le plafond Brave tient en une seule instruction SQL gardée, pas en lecture puis écriture.
- **Revue finale back :** une note hors bornes ne fait plus échouer toute la session ; la page est écartée sans note. Le Conseil réutilisera ce parcours en phase 4.

## Revue finale et corrections

- Back : 0 Critical, 2 Important, corrigés dans 2d4909b avec un Minor, re-revue approuvée.
  - I1 : appels Brave cadencés (1,1 s par clé) et réservation rendue quand Brave n'a ni servi ni facturé.
  - I2 : `structured_output_invalid` attrapé page par page (« Note impossible à établir. »).
  - m6 : une `OSError` au lancement du worker PDF rend la page illisible au lieu d'une erreur interne.
- Front : 0 Critical, 1 Important, corrigé dans 9116443 avec deux Minors, re-revue approuvée.
  - I1 : un plafond invalide bloque « Enregistrer ».
  - m2 : l'essai affiche pause, reprise et annulation.
  - m3 : une seule entrée de navigation active.

## Points laissés pour plus tard

### Phase 4
- Logger `httpx2` (SDK Z.ai) en INFO : il journalise l'URL fixe de l'API ; le passer en WARNING comme `httpx`.
- Rejeu de `judge` : le LLM est rappelé pour les pages déjà notées ; pas de `JUDGE_TIMEOUT_S` dédié.
- Une erreur de base pendant le rendu d'une réservation Brave bloque le repli vers le fournisseur suivant.

### Plus tard (mineurs triés « laisser »)
- 3.1 : `learn_lock` pris après la lecture du document ; une quinzaine de clics simultanés peuvent épuiser le pool.
- 3.6 : verrou de session tenu pendant les attentes SQLite ; crash pendant l'appel Brave refacturé une fois au rejeu ; requêtes vides ou échouées non comptées dans le plafond de session mais consommant une réservation Brave ; 9 autres Minors.
- 3.7 : `source.found` réémis au rejeu (le front regroupe par `source_id`) ; page illisible stockée « écartée » avec une note 0 ; source retenue écrite deux fois en mémoire par deux sessions ; `tool.called` émis après l'appel.
- Une attente de cadence annulée garde sa réservation Brave (une requête au plus) ; la cadence est propre au processus.
- Gotenberg n'est pas soumis au délai par domaine.
- GitHub sans jeton (60 appels par heure) ; intervalle arXiv de 3 s partagé par tous les utilisateurs.
- Session Archiviste en pause : pas de commande dans l'interface (inatteignable aujourd'hui).
- Carte de la clé Brave non marquée « facultative ».
- Front : Minors m1 et m4 à m9 de la revue finale ; TDD non strict sur `useRunningLearnings`.
