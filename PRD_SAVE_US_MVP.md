# SAVE-US — PRD MVP Hackathon

**Produit :** SAVE-US, CEMAC Emergency Network  
**Version :** MVP Hackathon — OpenAI Build Week  
**Date :** 21 juillet 2026
**Langue de l’interface MVP :** anglais uniquement  
**Marché de démonstration :** Cameroun ; architecture et sélecteur prêts pour les 6 pays CEMAC  
**Cible Devpost :** *Apps for your life*

## 1. Résumé

SAVE-US est une plateforme communautaire d’alerte et de vérification d’urgence pour la CEMAC. Elle permet aux citoyens vérifiés de déclarer des disparitions, des enlèvements présumés et des accidents routiers graves. Les établissements médicaux vérifiés constituent le rôle prévu pour le futur parcours de personne inconnue, amnésique ou inconsciente prise en charge.

Les agents IA structurent les déclarations, détectent les informations manquantes et les doublons, évaluent le risque de fraude et produisent une fiche d’alerte partageable. La diffusion est géociblée par pays, région et préférences d’alerte afin de diffuser vite sans noyer les utilisateurs sous des notifications non pertinentes.

Le MVP démontre surtout un parcours de disparition au Cameroun, tout en incluant les parcours d’enlèvement présumé et d’accident routier, la modération humaine, l’administration restreinte et le partage public sûr. Le parcours dédié de patient hospitalier inconnu reste différé après le hackathon.

## 2. Problème et proposition de valeur

Les informations critiques circulent souvent tardivement, de manière dispersée et sans vérification cohérente. SAVE-US propose une première couche civique : elle n’est ni un service d’urgence ni une autorité d’enquête. Elle accélère la collecte structurée, la cohérence des signalements et la diffusion responsable auprès des personnes les plus susceptibles d’aider.

**Promesse :** une alerte claire, vérifiée par IA selon des règles explicites, envoyée à la bonne communauté et immédiatement partageable.

## 3. Objectifs du MVP

1. Permettre à un citoyen connecté de déposer une disparition au Cameroun.
2. Montrer une analyse IA explicable : données extraites, champs manquants, doublons potentiels, score de confiance et score de risque/fraude.
3. Publier une alerte si elle respecte les règles de sécurité et de confiance.
4. Cibler les abonnés du même pays et de la région concernée, selon leurs réglages.
5. Générer une fiche d’alerte en anglais, imprimable/PDF et partageable.
6. Démontrer les trois parcours opérationnels (disparition, enlèvement présumé et accident routier) ; conserver le patient hospitalier inconnu comme évolution explicitement différée.

### Indicateurs de succès de la démo

- Une déclaration complète devient une alerte publiée en moins de trois minutes.
- L’IA explique sa décision sans révéler de raisonnement interne : statut, champs manquants, doublon potentiel et motifs de blocage.
- Au moins un destinataire de démonstration reçoit l’alerte dans le flux et dans un e-mail simulé.
- Le partage WhatsApp et le lien public portent automatiquement la mention « Source: SAVE-US ».

## 4. Périmètre

### Inclus dans le MVP

- Application web responsive en anglais.
- Inscription par numéro de téléphone ; OTP simulé pour le hackathon.
- Nom d’affichage obligatoire respectueux de la vie privée, puis profil : pays, région principale, régions supplémentaires suivies, catégories d’alertes activées.
- Catalogue complet des pays et subdivisions CEMAC fourni par le porteur du projet.
- Fil d’alertes géociblé et recherche simple par nom/statut.
- Déclarations complètes de disparition, enlèvement présumé et accident routier ; le parcours de patient hospitalier inconnu est différé.
- Analyse IA, doublon, modération minimale, génération de fiche et partage.
- Administration restreinte : vérification hospitalière privée, demandes motivées d’accès modérateur et gestion des rôles, règles de sûreté bornées, journal d’audit et tableau opérationnel agrégé avec boîte de travail privée et compteurs d’action.
- Statuts d’alerte, signalement d’erreur/fausse alerte et retrait motivé par le déclarant.
- E-mail de démo et centre de notifications in-app.
- Bannière de non-substitution aux services d’urgence.

### Hors périmètre du MVP

- Paiement réel de 104 XAF, Mobile Money et intégrations opérateurs.
- SMS, notifications push natives, WhatsApp Business API et synchronisation avec les autorités.
- Application iOS/Android native.
- Carte temps réel détaillée ; le fil d’alertes est la vue principale du MVP.
- Badge « validé par les autorités », commentaires publics, réseau social interne.
- Publication hospitalière réelle sans vérification manuelle préalable.
- Formulaire et publication dédiés de patient hospitalier inconnu, y compris son renouvellement par l’hôpital.

## 5. Utilisateurs et droits

| Rôle | Capacités MVP |
|---|---|
| Citizen / subscriber | Consulte, règle ses alertes, marque « seen », partage, signale une erreur. |
| Reporter | Citoyen avec téléphone vérifié ; crée une disparition, un enlèvement ou un accident. |
| Hospital representative | Compte institutionnel vérifié manuellement et par document ; rôle prêt pour le futur parcours de patient inconnu. |
| Moderator | Consulte les alertes à risque, doublons et demandes de retrait ; décide publication/suspension. |
| Administrator | Vérifie les hôpitaux, gère les modérateurs et les règles. |

Un même utilisateur peut être à la fois citoyen et déclarant. Les alertes restent gratuites à consulter et à recevoir ; le produit affiche une invitation non bloquante à soutenir SAVE-US à hauteur de **104 XAF/year**.

## 6. Types d’alerte et règles de diffusion

| Type | Créateur autorisé | Données minimales | Diffusion par défaut | Expiration |
|---|---|---|---|---|
| Missing person | Téléphone vérifié | Nom, âge, photo, sexe, date, dernier lieu vu, contact familial | Région concernée ; autres régions si préférences | 7 jours |
| Suspected abduction | Téléphone vérifié | Photo, lieu, date/heure, description | Tout le pays | 30 jours |
| Unknown hospital patient | Hôpital vérifié | Tranche d’âge, sexe, signe distinctif, hôpital, contact du service ; photo si possible | Tout le pays | Prévu après le hackathon : 3 jours, renouvelable par l’hôpital |
| Serious road accident | Téléphone vérifié | Position GPS ; photo/vidéo, victimes et besoin immédiat facultatifs | Région de l’accident ou rayon géographique | 24 h par défaut, clôture manuelle possible |

L’expiration de 24 heures pour les accidents routiers est une décision de cadrage MVP, faute de durée fournie ; elle devra être validée avec les futurs partenaires de secours.

## 7. Ciblage et préférences

À l’inscription, l’utilisateur choisit un nom d’affichage responsable obligatoire, puis un pays et une région principale. Il peut ensuite modifier son nom d’affichage, ces choix, suivre des régions additionnelles et activer/désactiver chaque catégorie.

Règles de sélection d’un destinataire :

1. Le pays de l’alerte doit correspondre au pays choisi par le destinataire.
2. Pour une disparition ou un accident, le destinataire doit suivre la région concernée (ou être dans le rayon, lorsque celui-ci existe).
3. Pour un enlèvement, tout utilisateur du pays ayant activé la catégorie est éligible. La règle patient inconnu est réservée au parcours différé.
4. Une préférence explicite de désactivation prévaut toujours.

## 8. Workflow IA et décision de publication

### Agent de première ligne

L’assistant guide le déclarant, pose les questions nécessaires, transforme ses réponses en champs structurés et demande les éléments manquants. Il génère ensuite un résumé public en anglais et une fiche de recherche.

### Contrôles IA

- Vérification de complétude et cohérence (âge, dates, pays/région, format des contacts).
- Recherche de doublons dans les alertes actives à partir du nom, de l’âge, de la photo et du dernier lieu connu.
- Modération des images/vidéos d’accident : contenu graphique ou choquant refusé avec une explication simple.
- Calcul de deux scores indépendants :
  - **Confidence score** : qualité et cohérence du signalement ; publication automatique possible à partir de **80/100**, sous réserve des règles de sécurité.
  - **Fraud-risk score** : probabilité qu’un signalement soit trompeur ; à partir de **80/100**, blocage automatique de la publication et envoi au modérateur.

L’IA ne contacte jamais une autorité et ne prétend jamais confirmer un fait. Les cas bloqués, les doublons et les alertes sensibles sont visibles dans la file des modérateurs. Une alerte d’enlèvement ayant un confidence score supérieur ou égal à 80 peut être publiée immédiatement dans le pays, tout en étant mise dans cette file pour revue a posteriori.

## 9. Parcours de démonstration principal

1. **Onboarding** — Amina crée un compte avec un numéro camerounais simulé, sélectionne Cameroon et Centre, puis active les alertes Missing person et Suspected abduction.
2. **Report missing person** — Une famille renseigne les informations requises et téléverse une photo.
3. **AI review** — SAVE-US affiche les données extraites, détecte l’absence éventuelle d’information, compare les alertes existantes et présente les deux scores.
4. **Publish** — Si les contrôles passent, l’alerte est publiée pour Centre. Une fiche PDF et un lien de partage sont créés.
5. **Receive and share** — Amina voit l’alerte dans son fil, reçoit un e-mail de démo, marque l’alerte comme vue et l’ouvre dans WhatsApp avec l’attribution SAVE-US.
6. **Close the loop** — Le déclarant peut signaler « Found » ou retirer l’alerte avec justification ; le statut public est mis à jour.

## 10. Écrans MVP

1. Landing page : mission, avertissement urgence, bouton « Join SAVE-US ».
2. Phone sign-in / OTP.
3. Onboarding : pays, région, préférences d’alertes.
4. Alert feed : filtres pays/région/type/statut ; cartes d’alerte.
5. New report : choix du type, assistant et formulaire structuré.
6. AI review : résumé, données détectées, contrôles, scores, décision.
7. Public alert detail : informations sûres, statut, partage, « Seen », signalement d’erreur.
8. Reporter dashboard : alertes créées, renouvellement, retrait motivé, « Found ».
9. Moderator queue : éléments bloqués ou à risque.
10. Settings : pays/région principale, régions suivies, catégories et rappel de contribution.
11. Administration : vérifications hospitalières privées, demandes et gestion des accès modérateur, règles de sûreté, journal d’audit, notifications opérationnelles privées et tableau de bord agrégé réservés aux administrateurs.

## 11. Protection, sûreté et vie privée

- Afficher sur chaque écran de déclaration : « SAVE-US does not replace emergency services. Contact local emergency services immediately when lives are in danger. »
- Ne pas afficher le numéro familial : afficher un bouton WhatsApp/« Contact family » qui ouvre un lien contrôlé.
- Ne pas afficher une adresse exacte ni les coordonnées GPS précises au public ; arrondir la position ou montrer seulement la région/zone. Les coordonnées précises restent réservées au déclarant et aux modérateurs.
- Pour les mineurs et les patients inconnus, limiter les informations à celles indispensables à l’identification ; utiliser une photo uniquement lorsque sa publication est justifiée.
- Désactiver les commentaires publics. Les utilisateurs peuvent partager, marquer une alerte vue et signaler une erreur avec justificatif.
- Exiger un motif pour tout retrait. Conserver un journal d’audit non public : auteur, dates, score, décision et justification.

## 12. Données principales

| Entité | Champs essentiels |
|---|---|
| User | id, téléphone vérifié, rôle, pays, région principale, statut de contribution |
| AlertPreference | user_id, catégories actives, régions suivies, e-mail activé |
| Alert | id, type, statut, pays, région, zone approximative, auteur, dates, expiration, contenu public |
| MissingPersonDetails | nom, âge, sexe, photo, dernier lieu vu, date, vêtements, contact privé, circonstances |
| AIReview | alert_id, résumé, données manquantes, doublons, confidence_score, fraud_risk_score, décision, motifs |
| Media | alert_id, chemin privé, type, résultat de modération, version publique éventuelle |
| Notification | destinataire, alerte, canal, statut de livraison/lecture |
| ReportAction | retrait, « found », correction, fausse alerte et décisions de modération ; justification privée |
| HospitalVerificationRequest | demande institutionnelle privée, décideur, décision et motif |
| ModeratorAccessRequest | motif privé du demandeur, statut, décideur, décision et motif |
| Notification | élément privé pour son destinataire ; les éléments opérationnels ne référencent que la demande administrative autorisée |
| SafetyRule / AdministrationAuditEntry | seuil borné, auteur, action, ancienne/nouvelle valeur, motif immuable et référence de demande autorisée |

Statuts d’alerte : `draft`, `ai_review`, `needs_moderation`, `published`, `rejected`, `reported_found`, `withdrawn`, `expired`.

## 13. Architecture recommandée

### Choix : Flask monolithe pour le hackathon

| Couche | Proposition |
|---|---|
| Web | Flask + Jinja templates + Bootstrap ou Tailwind via CDN |
| Données | SQLite + SQLAlchemy ; données de démonstration préchargées |
| Auth | OTP simulé ; interface compatible avec un futur Firebase Authentication |
| IA | OpenAI Responses API côté serveur : extraction structurée, résumé, détection de doublon et décision JSON |
| Médias | Stockage local de démo ; abstraction prête pour Cloudinary/S3 |
| PDF | HTML/CSS vers PDF ou génération serveur d’une fiche |
| E-mail | service SMTP de test / console locale, avec destinataires de démonstration |

**Pourquoi Flask :** très rapide pour un développeur solo, peu de conventions, parfait pour un flux serveur/Jinja et une démonstration cohérente.  
**Limite :** moins d’administration et de batteries incluses que Django ; la séparation API/mobile devra être renforcée après le hackathon.

### Alternatives considérées

| Stack | Forces | Faiblesses pour ce délai |
|---|---|---|
| Django | Admin, authentification et ORM très complets | Plus de configuration et de conventions à absorber en deux jours |
| FastAPI + React | API typée, excellente base mobile/API | Deux couches à construire ; cadence plus lente en solo |
| Next.js + Supabase | Très bon pour un produit web moderne et auth/données rapides | Changement de stack et dépendance cloud plus élevés |

## 14. Charte graphique MVP

Le logo fourni est l’autorité visuelle. L’interface doit évoquer protection, réseau et urgence sans adopter un ton anxiogène.

| Usage | Couleur indicative |
|---|---|
| Primary / protection | Navy `#003F70` |
| Secondary / network | Blue `#1284BD` |
| Soft information | Sky `#86CBE8` |
| Urgence et action principale | Orange `#FF6A00` |
| Fond | Off-white `#F7FAFC` |
| Texte | Navy `#0B2740` |

- Police : Inter ou system sans-serif ; titres nets et lisibles sur mobile.
- Bouton principal : orange ; actions ordinaires : bleu marine.
- États : danger rouge réservé au blocage ou au risque ; jamais utilisé pour une alerte simplement active.
- Cartes d’alerte : type, statut, pays/région, date, photographie cadrée avec respect, CTA de partage.
- Le logo est affiché sur l’accueil et l’en-tête ; sa version compacte sert de favicon/app mark.

## 15. Plan d’exécution sur deux jours

### Jour 1 — chemin heureux

1. Initialiser Flask, styles et données CEMAC.
2. Créer onboarding, profil et préférences.
3. Construire le flux Missing person, le modèle Alert et le fil ciblé.
4. Intégrer l’analyse IA avec un jeu de données de démonstration de secours.

### Jour 2 — preuve produit et soumission

1. Ajouter partage, fiche PDF, e-mail simulé, « seen », retrait et signalement.
2. Ajouter les formulaires secondaires et la file modérateur.
3. Vérifier la sécurité des affichages, les cas de blocage IA et le responsive mobile.
4. Préparer une vidéo de démo de 2–3 minutes, captures et soumission Devpost.

## 16. Critères d’acceptation

- Un nouvel utilisateur ne peut pas finaliser son inscription sans un nom d’affichage de 2 à 120 caractères ; il peut ensuite le modifier dans Profile & account.
- Un utilisateur peut choisir Cameroon/Centre, puis modifier son pays, sa région et ses préférences.
- Une disparition ne peut pas être soumise sans les champs obligatoires.
- Une soumission avec confidence score ≥ 80 et fraud-risk score < 80 peut être publiée.
- Une soumission avec fraud-risk score ≥ 80 est bloquée et visible seulement dans la file modérateur.
- Un doublon potentiel ne peut pas être publié automatiquement.
- Une alerte publiée de disparition n’est distribuée qu’aux utilisateurs éligibles du même pays et des régions suivies.
- Le numéro familial et la position exacte ne sont jamais rendus publics.
- Le lien de partage inclut l’attribution SAVE-US.
- Une alerte peut être signalée, retirée avec motif, marquée « found » et expirer selon sa catégorie.
- Les actions administratives sensibles nécessitent un motif, sont auditées et restent réservées aux administrateurs.
- Les administrateurs reçoivent des notifications in-app privées pour les vérifications hospitalières et demandes d’accès modérateur en attente ; l’espace de travail et la navigation n’affichent que des compteurs agrégés, retirés dès qu’une décision est enregistrée.

## 17. Évolutions après le hackathon

- Français, espagnol, puis langues locales.
- Firebase Authentication réel, Mobile Money et opérateurs télécoms.
- Application mobile et notifications push/SMS/WhatsApp Business.
- Cartographie, rayons géographiques et intégrations hôpitaux/autorités.
- Vérification d’autorités et badge officiel.
- Parcours complet de patient hospitalier inconnu : formulaire réservé à l’hôpital vérifié, revue, publication nationale, expiration et renouvellement.
- Politique de conservation des données, accords institutionnels et revue juridique locale pour chaque pays CEMAC.
