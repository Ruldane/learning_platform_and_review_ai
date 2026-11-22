# Phase 42 · Application mobile

L’écran mobile prépare le brief et les fiches du compte sur cet appareil après
un choix explicite. Il reste accessible après rechargement hors connexion.
Les réponses sont associées à l’échéance de la fiche et à un reçu par compte.
Le serveur reconnaît un rejeu et écarte une fiche déjà traitée. Oublier le
compte efface la copie, la file locale et invalide les écritures en vol.

La recette Playwright sous Edge a ouvert le build de production en mode mobile,
rechargé l’écran hors connexion, répondu et retrouvé la réponse synchronisée au
retour du réseau. Les contrôles ciblés ont vérifié les doublons et l’effacement.

Les notifications d’offres et les rappels Agenda sont vérifiés pendant que la
page mobile est ouverte, après autorisation du navigateur. Le prochain
créneau confirmé peut déclencher un rappel dans les 30 minutes précédentes.
Sur un téléphone, servir l’application en HTTPS pour l’installation.
[Installation d’une PWA](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable)
