# Bilan de la phase 1 (moteur d'agents)

Tag `phase-1`. 12 tâches, revue complète Opus high (0 Critical, 5 Important, 8 Minor), une vague de corrections approuvée en re-revue (13/13), suivi N1/N3. Tests : back 534 passés / 1 ignoré, front 313.

Contrôle de fin de phase sous Docker avec GLM 5.3 flash réel :
- un débat « apprendre Rust » s'écrit au fil de l'eau, avec l'intention de chaque agent et le coût en direct ;
- après un redémarrage du back pendant une question, la page se reconnecte sur la même carte, sans doublon ;
- après un redémarrage pendant l'écriture, la session reprend seule puis termine ;
- 6 appels sont journalisés dans `llm_calls` avec leur coût ;
- après la vague finale, un message pendant une question ne bloque plus la carte ; un rechargement en pause affiche « En pause » + Reprendre.

Décisions : D40 à D59 dans `DECISIONS.md` (D48 en double renuméroté D55).

## Arbitrages pris pendant l'exécution

- 1.5 — `max_retries=0` dans les modèles construits ; `invoke()` possède les nouveaux essais et le plafond par nœud.
- 1.5 — GLM : glm-5.3* ne coupe pas le thinking → `reasoning_effort: low`, réponse vide renvoyée en nouvel essai.
- 1.5 — liste GLM = ids de `GET /models` ∪ modèles des préréglages ; préréglage « Tout GLM » = glm-5.3-flash sur les 4 niveaux (modèle payé par l'utilisatrice).
- 1.5 — callback de coût async sur la même boucle (D42) ; `CostTracker` dans `config["callbacks"]`, prix chargés dans la composition (D44).
- 1.6 — `bus.close` seulement sur completed/failed/cancelled (D42) ; détection de trou côté live + `EventBus.aclose()` (D42) ; verrou par session sur les actions de contrôle + porte de démarrage (D55, ex-D48).
- 1.7 — Origin vérifiée sur le WebSocket ; dépendances core en `HTTPConnection` ; `get_runtime` sur `app.state.runtime` ; codes 409 de D46, 503 `server_stopping`.
- 1.7 — fin de flux déterministe : fermeture 1000 sur l'événement final, ou dès que l'abonné a reçu jusqu'au `seq` de fin lu après abonnement (D50, D52) ; port `RunSettingsSource` + contrat 6 « app.agents ↛ app.features » ; pytest-timeout 60 s / 10 s pour les WS.
- 1.10 — fermeture 1000 définitive (lecture REST) ; 4404 envoyé après accept, visible du navigateur ; les autres refus arrivent en 1006 → backoff 0,5→8 s puis 10 s, arrêt après 8 reconnexions sans données (D47, D49).
- 1.11 — `features/*/components` peuvent importer `shared/session-ui` ; Board/SourcesPanel reportés en phase 4.
- 1.12 — `/demo` hors navigation (D54) ; confirmation d'annulation en carte, pas de dialogue navigateur ; contrôle Docker + navigateur et tag faits par le contrôleur.
- Organisation : agents parallèles seulement sur des fichiers disjoints, commits par chemins explicites, pas de `pre-commit --all-files` pendant qu'un autre agent écrit (le hook met de côté les fichiers non indexés).
- Vague finale (D56–D59) :
  - I1 : un message ne répond jamais à une question (D4).
  - I2 : statut REST lu à l'ouverture du flux, appliqué selon `seq` / `updated_at` ; `agent.started` ne lève plus une pause.
  - I3 : pannes du fournisseur en messages français lisibles (clé, crédit GLM 1113, surcharge 1305, 5xx, délai), sans corps brut.
  - I4 : usage en flux demandé pour OpenAI → tokens, coût et plafond fonctionnent.
  - I5 : un tour interrompu est retiré quand l'agent recommence ; une bulle ne reste « Écrit… » que si la session tourne.
  - M1 : compteur de reconnexion remis à zéro à l'ouverture.
  - M2 : « Nouveau débat » sur une session introuvable.
  - M3 : délai par appel 45 s < 120 s par nœud.
  - M6 : `EventBus.last_seq` supprimé.
  - M7 : `post_message` sous le verrou de contrôle.
  - N3 : code d'erreur fournisseur lu sans risque.

## Points laissés pour plus tard

### Phase 2 (dès l'ouverture)
- Découper `fr.ts` par zone + agrégateur, fusionner `session.*` et `sessions.*`.
- D52 §2 : statut final et événement final dans deux transactions. Choisir entre une transaction unique et une réparation au démarrage.
- Tests manquants :
  - pause/cancel pendant l'écriture de l'issue ;
  - cancel pendant `_settle` ;
  - redémarrage après claim resume ;
  - reconnexion WS pendant une publication active ;
  - double montage StrictMode ;
  - course check REST / nouveau socket.
- N2 : lecture REST sautée si une vérification est déjà en cours (impact quasi nul).
- N5 : `bus.flush()` attend les publications de toutes les sessions (borné).

### Phase 4 (Conseil)
- M4 : chaque remarque est renvoyée à chaque tour (choix démo D53) ; ne passer que les nouvelles.
- M5 : un INSERT + commit par token ; regrouper les tokens ou passer en `synchronous=NORMAL`.
- Store mis à jour à chaque token, liste d'événements sans plafond.
- `GET /sessions` sans pagination.
- Board / SourcesPanel, affichage des citations.

### Phase 9 (coûts, déploiement)
- Appel LLM interrompu par un redémarrage non journalisé dans `llm_calls` (coût perdu).
- Fabrique de socket qui lève (HTTPS / mixed content).

### Abandonnés
- Fenêtre résiduelle `_stopping` à l'arrêt.
- Cancel derrière une publication suspendue (borné par `busy_timeout`).
- Événement en vol après lecture de `max(seq)` sur une session annulée.
- Un seul `useMutation` pour les 4 actions (voulu : une action à la fois).
