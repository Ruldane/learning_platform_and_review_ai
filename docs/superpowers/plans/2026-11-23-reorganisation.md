# Réorganisation de Tremplin

> **Pour les agents :** utiliser superpowers:subagent-driven-development. Les tâches ci-dessous suivent la mission du 22 novembre et l’ajout sur Étudier.

**Objectif** — Retrouver chaque écran depuis six rubriques au plus, gérer les conversations du Cerveau et d’Étudier avec la même liste et rendre les opérations accessibles au MCP.

**Base** — `4c155a1c65dfe10ec7c71bb7d6e3edd02a743e51`, branche `codex/reorganisation`.

## Contraintes

Les chemins existants restent accessibles. Les interfaces exposent des libellés français, des états vides et un parcours clavier. Les suppressions MCP passent par le niveau 3. Les données pédagogiques et les notes du Cerveau vivent indépendamment de leurs conversations. Les essais utilisent des données et des modèles de test.

## Conversations du Cerveau et d’Étudier

- [x] Écrire une recette couvrant deux fils distincts, renommage, recherche, réouverture, vidage, suppression et effacement par espace.
- [x] Partager un registre de fils et les opérations de liste dans `conversations`. Conserver les anciens identifiants, les anciennes URL et les tours persistés par migration. Conserver les sessions pédagogiques utilisées comme références par les preuves et les fiches.
- [x] Enregistrer les leçons et le mode d’Étudier par fil. Filtrer les leçons et fils selon le compte. Supprimer les échanges et leur état d’exécution sur les opérations destructrices, sous le même verrou que la réservation des tours.
- [x] Exposer lecture et recherche au niveau 1, création, écriture et édition au niveau 2, vidage et suppressions au niveau 3. Vérifier les chemins et l’isolation entre comptes.
- [x] Brancher les deux écrans au même composant de liste et aux mêmes mutations. Vérifier navigation, confirmation et focus avec Playwright.

## Interface et repères

- [x] Inventorier les routes et outils. Organiser les usages autour de l’accueil, des études, du code, du Cerveau et de la carrière. Laisser les destinations secondaires au Labo et garder les routes actuelles.
- [x] Ajouter pages de rubrique, préférences d’épinglage et visite, sous-titres et réglages regroupés. Accès MCP aux préférences du Labo.
- [x] Afficher le relais, la progression et les exclusions du Cerveau ainsi que la disponibilité du fournisseur configuré.
- [x] Vérifier l’accessibilité, le menu, les anciens liens, les états vides et produire les captures.

## Couverture MCP

- [x] Répartir les routes par niveau et garder une liste fermée pour les secrets et la sécurité. Réutiliser les demandes de confirmation. Encadrer le contenu externe avant de le rendre au client.
- [x] Ajouter l’aperçu des rubriques, des actions et des prérequis. Vérifier les ressources non binaires, les consentements et l’isolement.
- [x] Régénérer le contrat OpenAPI et les types, puis exécuter les contrôles et le parcours Playwright. Rédiger le bilan et préparer un commit avec les hooks.
