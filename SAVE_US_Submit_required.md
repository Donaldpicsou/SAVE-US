# SAVE-US — Priorités de soumission au hackathon

Cette checklist priorise le travail qui renforcera le plus la soumission SAVE-US à OpenAI Build Week. Elle s’appuie sur les règles officielles et sur l’état actuel du MVP.

## Positionnement de la soumission

- **Catégorie recommandée :** Apps for Your Life.
- **Promesse principale :** SAVE-US aide les communautés d’Afrique centrale à structurer, examiner, diffuser de manière sûre et partager des alertes d’urgence critiques.
- **Différenciateur :** GPT-5.6 agit comme enquêteur de première ligne : il structure les signalements, relève les informations absentes ou incohérentes, détecte des doublons possibles, évalue confiance et risque de fraude, puis applique les règles de ciblage par pays et région.
- **Engagement de sûreté :** SAVE-US ne vérifie pas les faits, ne contacte pas les autorités et ne remplace pas les services d’urgence. La plateforme protège contacts privés, adresses précises, coordonnées et médias originaux téléversés.

## Priorité 0 — Obligatoire avant la soumission

### État de préparation actuel

- Les tâches produit T1–T54 sont terminées, y compris le workflow administrateur renforcé T41–T48 (demandes privées hôpital et accès modérateur, notifications de boîte de travail, compteurs et audit) et les fiches/PDF/partages sûrs T49–T54.
- Les priorités restantes sont donc opérationnelles et de soumission : déploiement stable, démo réelle OpenAI, vidéo Devpost, page Devpost et preuves du travail.
- Le parcours complet `Unknown hospital patient` est volontairement différé après la soumission ; ne pas le présenter comme disponible.

### 1. Maintenir les README et la licence — Terminé

`README.md`, `README_FR.md` et la licence MIT sont présents. Ils documentent maintenant le flux effectif de fiches et de partage : HTML A4, PDF côté serveur, liens opaques, actions WhatsApp/Web Share, limites de confidentialité, accès démo, installation et tests. Les maintenir à jour avant toute soumission si le MVP évolue.

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
   Montrer la fiche HTML/PDF imprimable et le partage WhatsApp sûr avec `Source: SAVE-US` ; expliquer que le lien est opaque, révocable et ne contient aucun média original.
6. **2:20–2:40 — Règles multi-événements**
   Comparer un enlèvement national à un accident routier régional et son expiration.
7. **2:40–2:50 — Contribution Codex et impact**
   Expliquer comment Codex a accéléré le MVP et pourquoi l’approche peut s’étendre de manière responsable dans la CEMAC.

## Promesse PRD terminée — Fiche, PDF et partage sécurisé (T49–T54)

T49–T54 sont terminées. Les alertes publiées disposent désormais d’une fiche HTML A4 aux couleurs SAVE-US, d’un PDF côté serveur et d’actions de partage depuis le détail. L’URL externe est opaque, révocable, expire au plus tard après sept jours ou avec l’alerte, et cesse de fonctionner après retrait, rejet ou expiration. Les tests E2E contrôlent HTML, texte extrait du PDF, attribution anglaise, charge utile WhatsApp, révocation et exclusion des médias/données privés.

La fiche et le lien de partage externe mis en œuvre n’exposent jamais :

- les contacts privés de la famille ou du déclarant ;
- une adresse précise ou des coordonnées GPS ;
- les circonstances privées ou motifs internes de modération ;
- le média original téléversé.

Toute future photo partageable à l’extérieur exigera une approbation explicite de modération et devra être une copie dérivée, non le média privé d’origine. Le MVP actuel ne partage aucun média d’incident à l’extérieur.

## Promesse PRD terminée — Administration responsable (T41–T48)

T41–T48 sont terminées. Les administrateurs disposent d’un espace privé pour examiner les demandes de vérification hospitalière et d’accès modérateur motivées, gérer les modérateurs actifs avec protections contre l’auto-blocage, ajuster des règles de sûreté bornées et consulter un journal d’audit minimisé. Des notifications in-app privées et badges adaptés au rôle remontent les travaux en attente ; le tableau de bord orienté action agrège volumes, délais, alertes actives/en attente/expirées, demandes hospitalières et d’accès modérateur, ainsi que l’activité des modérateurs sans exposer le contenu privé des signalements. Le parcours est couvert par des tests E2E automatisés.

## Priorité 1 — Renforcer la démonstration technique

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

## Priorité 2 — Présentation Devpost et preuves

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
- [x] Flux fiche imprimable/PDF/partage fonctionnel et couvert par des tests E2E de sûreté.
- [x] Workflow administrateur et protections d’accès couverts par un test E2E.
