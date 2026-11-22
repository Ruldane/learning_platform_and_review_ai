# Phase 24 · Révision par messagerie

Dans **Réglages → Révision par messagerie**, l’utilisatrice autorise un créneau dans le fuseau de son compte et associe le jeton MCP dédié de Nod à une discussion Telegram privée. Nod réserve une fiche due. Le même défi revient pendant le créneau et un seul avis est enregistré par défi. Désactiver le consentement ou révoquer le jeton coupe le parcours. La route générique de révision reste réservée à l’interface.

L’avis explicite passe par le service de révision des fiches. L’échéance et le résultat rejouable sont validés dans la même transaction. L’historique MCP permet d’annuler l’avis tant que ses données sont compatibles avec l’annulation. Nod conserve l’identifiant de défi dans son état pour dédupliquer l’envoi Telegram. Le [guide de branchement](../../mcp/revision-telegram.md) décrit le contrat.

Le parcours Edge a utilisé une base SQLite jetable et un Nod factice connecté au vrai MCP local. Il a vérifié le consentement au clavier, deux passages pour un seul message, la révélation du verso, le rejeu de l’avis et la progression d’une seule fiche. Les deux serveurs et les fichiers temporaires de recette ont été retirés. L’isolation a été testée avec deux comptes et un fournisseur Google local simulé. La migration de ce worktree est `0035_message_review`, après `0034`.
