# SAVE-US — Priorités de soumission au hackathon

Cette checklist priorise le travail qui renforcera le plus la soumission SAVE-US à OpenAI Build Week. Elle s’appuie sur les règles officielles et sur l’état actuel du MVP.

## Positionnement de la soumission

- **Catégorie recommandée :** Apps for Your Life.
- **Promesse principale :** SAVE-US aide les communautés d’Afrique centrale à structurer, examiner, diffuser de manière sûre et partager des alertes d’urgence critiques.
- **Différenciateur :** GPT-5.6 agit comme enquêteur de première ligne : il structure les signalements, relève les informations absentes ou incohérentes, détecte des doublons possibles, évalue confiance et risque de fraude, puis applique les règles de ciblage par pays et région.
- **Engagement de sûreté :** SAVE-US ne vérifie pas les faits, ne contacte pas les autorités et ne remplace pas les services d’urgence. La plateforme protège contacts privés, adresses précises, coordonnées et médias originaux téléversés.

## Priorité 0 — Obligatoire avant la soumission

### 1. Créer un README complet et ajouter une licence

Créer `README.md` avant la soumission finale. Il doit inclure :

- L’objectif du projet et le problème CEMAC traité.
- Les fonctionnalités principales effectives et les limites connues du MVP.
- Les instructions d’installation : environnement Python, dépendances, migration, données démo et commande de lancement local.
- Les instructions d’accès à la démo, y compris l’OTP simulé et le code `123456`.
- La commande de test : `.venv/bin/python -m unittest discover -s tests -q`.
- Un résumé de l’architecture : Flask, SQLite, SQLAlchemy, stockage média privé, OpenAI Responses API et repli déterministe.
- Les choix de sécurité et confidentialité : médias protégés, absence de contacts privés publics, localisation approximative, alertes ciblées et piste d’audit.
- Une section **« Built with Codex and GPT-5.6 »** expliquant :
  - où Codex a accéléré l’implémentation, les tests, l’intégration visuelle et la documentation ;
  - quelles décisions produit, techniques et de sûreté ont été prises délibérément par l’équipe ;
  - comment GPT-5.6 est utilisé pour les revues structurées côté serveur et la modération des médias d’accident ;
  - comment le repli déterministe maintient la démo disponible sans clé API.
- Une distinction claire entre le travail créé ou significativement étendu pendant le hackathon et tout travail antérieur.

Ajouter une licence open source adaptée au dépôt public.

### 2. Fournir une démo utilisable par les juges

- Déployer SAVE-US sur une URL publique stable, ou fournir une version de test entièrement reproductible.
- Vérifier migrations et données démo sur l’environnement déployé.
- Documenter un compte, numéro de téléphone et code OTP de test.
- Vérifier que l’application fonctionne sans intervention manuelle en base de données.
- Laisser la démo gratuite et disponible pendant toute la période de jugement.

### 3. Enregistrer la vidéo de démonstration Devpost

- La publier sur YouTube et la rendre publique.
- Rester sous **trois minutes**.
- Inclure un audio clair.
- Montrer ce qui a été construit et comment Codex et GPT-5.6 ont été utilisés.
- Ne pas utiliser de musique non licenciée, de marques tierces ou de données personnelles.

Structure vidéo suggérée, en 2 min 50 :

1. **0:00–0:20 — Problème et promesse**
   Présenter le déficit d’information d’urgence en Afrique centrale et l’approche SAVE-US centrée sur la sûreté.
2. **0:20–1:05 — Signalement de disparition**
   Montrer l’onboarding Cameroun/Centre, un signalement structuré et le téléversement protégé d’une photo.
3. **1:05–1:35 — Revue GPT-5.6**
   Montrer résumé sûr, données extraites, champs manquants, doublon possible, confiance et risque de fraude. Préciser que la revue est côté serveur via GPT-5.6/OpenAI Responses API.
4. **1:35–2:00 — Ciblage et modération**
   Montrer la notification/le fil d’un destinataire éligible et une décision modérateur avec motif d’audit.
5. **2:00–2:20 — Fiche d’alerte partageable**
   Montrer la fiche imprimable/PDF et le partage WhatsApp sûr avec `Source: SAVE-US`, une fois implémentés.
6. **2:20–2:40 — Règles multi-événements**
   Comparer un enlèvement national à un accident routier régional et son expiration.
7. **2:40–2:50 — Contribution Codex et impact**
   Expliquer comment Codex a accéléré le MVP et pourquoi l’approche peut s’étendre de manière responsable dans la CEMAC.

## Priorité 1 — Achever la promesse PRD principale encore incomplète

### 4. Livrer la fiche d’alerte, le PDF et le partage (roadmap T49–T54)

Les boutons du détail d’alerte ne sont pas encore fonctionnels. Réaliser cette branche dans l’ordre suivant :

- **T49 :** définir un contrat unique de fiche d’alerte anglaise, publique et sûre.
- **T50 :** construire une fiche HTML A4 imprimable et aux couleurs SAVE-US.
- **T51 :** générer un PDF côté serveur depuis le même contenu sûr.
- **T52 :** créer des liens de partage opaques, révocables et expirables.
- **T53 :** ajouter copie du lien, repli Web Share et partage WhatsApp prérempli avec `Source: SAVE-US`.
- **T54 :** tester impression, PDF, texte anglais, attribution, liens révoqués et exclusion des données privées.

La fiche et le lien de partage externe ne doivent jamais exposer :

- les contacts privés de la famille ou du déclarant ;
- une adresse précise ou des coordonnées GPS ;
- les circonstances privées ou motifs internes de modération ;
- le média original téléversé.

Toute photo partageable à l’extérieur exige une approbation explicite de modération et devrait être une copie dérivée, non le média privé d’origine.

## Priorité 2 — Renforcer la démonstration technique

### 5. Démontrer un usage réel d’OpenAI

- Configurer une démo avec `OPENAI_API_KEY` uniquement dans l’environnement de l’hébergeur.
- Utiliser l’intégration existante côté serveur avec Responses API et `gpt-5.6`.
- Rendre visible dans la démo la source de revue (`openai_responses_api` ou repli déterministe).
- Conserver le repli pour que l’application reste utilisable si l’API est indisponible.
- Ne jamais commiter de clé ni l’inclure dans les captures, la vidéo, la documentation ou les données de test.

### 6. Sécuriser l’expérience de démonstration

- Retirer ou compléter tout bouton visible mais inactif.
- Utiliser un jeu de données démo déterministe, répété avant l’enregistrement.
- Conserver un parcours vidéo principal centré sur une disparition, puis montrer brièvement les ciblages enlèvement et accident.
- Ne pas présenter le parcours « Unknown hospital patient » comme terminé avant son formulaire dédié et son workflow de vérification.

## Priorité 3 — Présentation Devpost et preuves

### 7. Préparer la page Devpost

- Sélectionner **Apps for Your Life**.
- Rédiger la description en anglais.
- Inclure : problème, audience, solution, workflow IA, limites de sûreté, architecture, identifiants de démo et roadmap.
- Ajouter 3 à 5 captures montrant onboarding, signalement, revue IA, fil d’alertes, modération et fiche de partage.
- Lier le dépôt de code public.
- Fournir le Session ID Codex `/feedback` du thread où l’essentiel de la fonctionnalité a été construit.
- Ajouter l’URL publique de la vidéo YouTube.

### 8. Conserver les preuves du travail de hackathon

- Conserver les commits datés ainsi que l’historique PRD/roadmap.
- Conserver le thread Codex utilisé pour construire le cœur du projet.
- Décrire clairement dans le README le travail ajouté ou significativement étendu pendant la période de soumission.

## À déprioriser après la soumission

Ces travaux sont utiles mais ne doivent pas retarder les éléments ci-dessus :

- Tableaux de bord administrateur et workflow de vérification hospitalière (T41–T48).
- Applications mobiles natives.
- Paiement réel, Mobile Money, SMS, push ou WhatsApp Business API.
- Intégrations avec les autorités et badges publics de vérification.
- Parcours complet de signalement d’un patient hospitalier inconnu.

## Vérification finale de soumission

- [ ] Dépôt public ou accessible aux juges, README et licence.
- [ ] URL fonctionnelle ou build local reproductible avec identifiants de test.
- [ ] Migrations et données démo validées depuis un environnement propre.
- [ ] Vidéo YouTube publique, audio inclus, moins de trois minutes.
- [ ] Vidéo expliquant l’usage de Codex et GPT-5.6.
- [ ] Description Devpost et instructions de test en anglais.
- [ ] URL dépôt, URL YouTube et Session ID Codex `/feedback` ajoutés sur Devpost.
- [ ] Aucune clé API, donnée personnelle réelle ou ressource non licenciée.
- [ ] Flux fiche imprimable/PDF/partage fonctionnel, ou fonctionnalité incomplète déclarée honnêtement comme roadmap.
