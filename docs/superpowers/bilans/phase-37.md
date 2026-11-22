# Phase 37 · Liaison GitHub

Le Portfolio permet de faire vérifier un commit à partir du formulaire de rendu.
Tremplin lit le dépôt public et vérifie que le SHA complet désigne un commit
dans l’historique de la branche par défaut. GitHub doit déclarer la signature
valide et rattacher l’auteur et le committer à un même compte personnel.
L’utilisatrice place un code temporaire dans la bio publique de ce compte, puis
rend son projet. Elle peut retirer le code après la vérification.

Le code expire après quinze minutes. Tremplin conserve son empreinte jusqu’à sa
consommation. Le rendu, sa session d’évaluation et la preuve sont enregistrés
ensemble. Un SHA déjà attribué compte une seule fois pour ce compte Tremplin.
Le projet garde le lien du commit et les compétences de son module reçoivent
une preuve de pratique, au niveau « En cours » au maximum pour cette preuve.

La source atteste à la date du rendu que l’utilisatrice peut modifier le profil
associé au compte auteur, et que GitHub rattache à ce compte la signature du
commit. La qualité du code relève de l’évaluation du projet. Cette attribution
porte sur la signature et le compte GitHub, sans identifier la personne
physique qui a écrit le code ni établir son originalité.

Les vérifications utilisent les [statuts de signature de GitHub](https://docs.github.com/en/authentication/managing-commit-signature-verification/about-commit-signature-verification)
et les [lectures publiques de l’API des commits](https://docs.github.com/en/rest/commits/commits).

La recette Edge avec GitHub factice a demandé un code, rendu le projet avec
le commit choisi, puis retrouvé la preuve de pratique depuis le nœud de la
compétence sur la carte. Les tests ciblés ont vérifié le refus d’un dépôt privé,
d’un commit mal attribué et d’un code absent ou expiré, ainsi que le rejeu et
l’isolation des comptes.
