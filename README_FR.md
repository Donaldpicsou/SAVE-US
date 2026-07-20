# SAVE-US — CEMAC Emergency Network

SAVE-US est un MVP civique d’alertes d’urgence, conçu pour l’Afrique centrale (CEMAC). Il aide les communautés à structurer, examiner, diffuser de manière sûre et partager des signalements critiques lorsque les canaux d’information traditionnels sont trop lents.

Construit pour **OpenAI Build Week 2026**, SAVE-US est présenté dans la catégorie **Apps for Your Life**.

> SAVE-US ne remplace ni la police, ni une ambulance, ni les pompiers, ni un hôpital, ni tout autre service d’urgence. Lorsqu’une vie est en danger immédiat, contactez d’abord les services d’urgence locaux.

## Le problème traité

Dans la zone CEMAC, familles, témoins et équipes de soins peuvent avoir des difficultés à centraliser et diffuser rapidement des informations concernant des disparitions, enlèvements présumés, patients inconnus ou accidents routiers graves. Les partages informels sont souvent lents, peu ciblés géographiquement et exposés à la désinformation ou à des atteintes à la vie privée.

SAVE-US répond à ce besoin avec un MVP web en anglais qui :

- accompagne un déclarant vérifié dans une collecte structurée ;
- utilise GPT-5.6 pour produire un résumé public sûr et relever données manquantes, doublons possibles, confiance et risque de fraude ;
- applique des règles explicites de publication et des garanties de modération humaine ;
- notifie uniquement les utilisateurs éligibles selon leur pays, leur région et leurs préférences ;
- conserve une piste d’audit privée pour les décisions sensibles.

La démonstration du MVP est centrée sur le Cameroun et la région du Centre, tout en conservant les données pays et régions de la CEMAC.

## Fonctionnalités effectives du MVP

### Signalement et revue

- Authentification par téléphone et OTP simulé.
- Validation des numéros CEMAC et onboarding pays/région principale.
- Préférences : catégories, régions suivies et préférence d’e-mail simulée.
- Parcours guidés et reprenables pour :
  - les personnes disparues ;
  - les enlèvements présumés ;
  - les accidents routiers graves.
- Validation côté serveur, brouillons et stockage local privé des photos.
- Revue IA structurée pour disparitions et enlèvements : résumé public anglais sûr, données extraites, champs manquants, doublons possibles, scores de confiance et de fraude, motifs et décision.
- Revue visuelle GPT-5.6 des médias facultatifs d’accident lorsqu’une clé API est configurée.

### Sûreté, publication et ciblage

- Publication uniquement lorsque les règles pertinentes sont satisfaites ; sinon passage en modération.
- Disparitions ciblées vers la région touchée et les régions suivies éligibles.
- Enlèvements présumés ciblés vers les abonnés éligibles de l’ensemble du pays concerné.
- Accidents routiers ciblés vers les abonnés régionaux éligibles, expirant après 24 h et clôturables avec motif.
- Notifications de publication, modération, clôture et expiration, avec état lu/non lu.
- Espace modérateur : revue privée, publication motivée, demande d’informations, rejet et retrait d’un enlèvement publié.
- Piste d’audit privée pour les clôtures et décisions de modération.

### Expérience produit

- Identité visuelle SAVE-US responsive, navigation partagée, footer, menus de notifications et de compte.
- Tableau de bord, fil d’alertes, détail, centre de notifications et espace déclarant.
- Données CEMAC et utilisateurs démo préchargés.
- Tests automatisés couvrant signalements, contrats IA, ciblage, notifications, médias protégés, modération et parcours de bout en bout.

## Limites connues du MVP

- L’application est une démonstration de hackathon et ne remplace pas les services d’urgence ou les autorités.
- OTP, e-mails et notifications sont simulés ; il n’existe pas d’intégration SMS, push ou WhatsApp Business réelle.
- Le type `Unknown hospital patient` existe dans le modèle métier et les préférences, mais son parcours de signalement dédié et sa vérification institutionnelle ne sont pas encore implémentés.
- Paiements, Mobile Money, intégrations avec les autorités, carte temps réel, applications mobiles natives et commentaires publics sont hors périmètre.
- L’IA assiste la revue de première ligne ; elle n’établit pas les faits et ne contacte pas les autorités.
- Les fiches d’alerte imprimables/PDF et liens externes sécurisés sont planifiés dans la roadmap (T49–T54).

## Technologies et architecture

SAVE-US utilise une architecture Flask volontairement légère et testable :

| Couche | Implémentation |
|---|---|
| Application web | Flask 3 et templates Jinja |
| Persistance | SQLite, SQLAlchemy et Flask-Migrate |
| Authentification | Session téléphone/OTP simulée |
| Médias | Stockage local privé hors de `static/`, validé côté serveur |
| Revue IA | OpenAI Responses API, GPT-5.6 et validation de sortie structurée |
| Résilience IA | Repli démo déterministe et transparent sans clé API ou en cas d’échec |
| Tests | Suite Python `unittest` |

### Flux général

```text
Déclarant vérifié
  → signalement structuré
  → revue GPT-5.6 ou repli déterministe
  → règle de publication / modération humaine
  → alerte ciblée par pays ou région
  → notification et fil pour les destinataires éligibles
```

## Choix de confidentialité et de sûreté

- **Médias protégés :** photos privées, accessibles uniquement au déclarant, au destinataire éligible ou au modérateur autorisé. Les requêtes non autorisées reçoivent `404`, avec réponses non cacheables.
- **Aucun contact privé public :** les coordonnées de la famille et du déclarant ne figurent jamais dans une alerte publique.
- **Localisation publique approximative :** une zone ou région approximative est affichée ; adresses précises et coordonnées GPS restent privées.
- **Ciblage par préférences :** un destinataire doit avoir un téléphone vérifié, le bon pays, la catégorie active et, si nécessaire, la région correspondante ou suivie.
- **Garanties humaines :** les dossiers à risque, incomplets, en doublon ou sensibles peuvent être envoyés à un modérateur.
- **Piste d’audit :** toute clôture ou décision de modération motivée conserve auteur, date, action et justification en privé.
- **Sûreté média :** les médias d’accident invalides, graphiques ou incertains sont bloqués ou modérés avant toute publication.

## Installation rapide

### Prérequis

- Python 3.11 ou version plus récente.
- `pip` et un terminal.
- Facultatif : une clé API OpenAI pour la revue GPT-5.6 réelle. Le repli démo fonctionne sans clé.

### 1. Cloner le dépôt et créer l’environnement virtuel

```bash
git clone https://github.com/Donaldpicsou/SAVE-US.git
cd SAVE-US
python3 -m venv .venv
source .venv/bin/activate
```

Sous Windows PowerShell :

```powershell
.venv\Scripts\Activate.ps1
```

### 2. Installer les dépendances et configurer les variables locales

```bash
pip install -r requirements.txt
cp .env.example .env
```

Modifier `.env` uniquement pour activer la revue IA réelle :

```dotenv
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-5.6
OPENAI_MEDIA_MODEL=gpt-5.6
```

Ne jamais commiter `.env` ou une clé API. Sans `OPENAI_API_KEY`, SAVE-US utilise son repli démo déterministe.

### 3. Créer et peupler la base de données

Utiliser les migrations pour une installation locale normale :

```bash
.venv/bin/flask --app run:app db upgrade
.venv/bin/python scripts/seed_demo_data.py
```

Le peuplement est idempotent : la commande peut être relancée sans dupliquer utilisateurs et préférences démo.

### 4. Lancer localement

```bash
.venv/bin/flask --app run:app run --debug
```

Ouvrir [http://127.0.0.1:5000](http://127.0.0.1:5000) dans le navigateur.

### Alternative de création locale des tables

Pour une base de démonstration minimale, l’outil suivant crée les tables depuis les métadonnées SQLAlchemy :

```bash
.venv/bin/python scripts/init_db.py
.venv/bin/python scripts/seed_demo_data.py
```

Pour le développement et le déploiement, privilégier les migrations Alembic.

## Accès à la démo

Tous les numéros préchargés utilisent le code OTP simulé :

```text
123456
```

Comptes démo utiles :

| Rôle | Nom | Numéro de téléphone | Pays / région |
|---|---|---|---|
| Déclarant | Amina N. | `+237612345678` | Cameroun / Centre |
| Abonné citoyen | David T. | `+237677123456` | Cameroun / Centre |
| Modératrice | Clarisse M. | `+237655334455` | Cameroun / Centre |
| Administrateur | SAVE-US Admin | `+237690001122` | Cameroun / Centre |
| Abonné régional | Jonas K. | `+237688445566` | Cameroun / Littoral |
| Abonné CEMAC | Paul E. | `+24174001122` | Gabon / Estuaire |

Pour vous connecter, saisir l’un de ces numéros puis `123456` sur la page OTP.

## Tests

Lancer l’ensemble des tests automatisés depuis la racine du dépôt :

```bash
.venv/bin/python -m unittest discover -s tests -q
```

La suite couvre validations métier, contrats OpenAI, repli déterministe, diffusion ciblée, accès média protégé, formulaires, décisions de modération et parcours démo Cameroun/Centre.

## Built with Codex and GPT-5.6

SAVE-US a été créé et significativement étendu pendant OpenAI Build Week 2026, avec Codex comme collaborateur d’implémentation et GPT-5.6 comme moteur de revue structurée.

### Comment Codex a accéléré le projet

Codex a accéléré :

- la structure Flask, migrations, entités SQLAlchemy et socle de tests ;
- l’intégration visuelle issue de Stitch, le shell responsive, la navigation, les menus de notification et les raffinements d’interaction ;
- les parcours de signalement, règles de validation, médias protégés, données CEMAC, logique de ciblage et espace de modération ;
- les tests de régression et scénarios de bout en bout ;
- le PRD, la roadmap, la checklist de soumission et la documentation du dépôt.

### Décisions délibérées de l’équipe

L’équipe a pris les décisions produit et techniques essentielles :

- adopter un modèle de coordination communautaire sûr sans prétendre à une vérification par les autorités ;
- distinguer diffusion nationale des enlèvements et diffusion régionale des disparitions/accidents ;
- maintenir contacts privés, localisations exactes et médias originaux hors du contenu public ;
- utiliser des seuils explicites de publication et une modération humaine pour les cas sensibles ;
- conserver un repli déterministe hors ligne pour une démo de hackathon fiable.

### Usage de GPT-5.6

Quand `OPENAI_API_KEY` est configurée, le serveur appelle l’OpenAI Responses API avec GPT-5.6. L’application valide les sorties structurées avant leur persistance. GPT-5.6 produit résumé public sûr, données extraites, champs manquants, doublons possibles, score de confiance, risque de fraude, décision et motifs pour disparitions et enlèvements.

Pour les médias facultatifs d’accident, GPT-5.6 réalise une vérification visuelle structurée. Les médias invalides, graphiques ou dangereux sont bloqués ; les cas incertains passent en modération humaine. Les contacts privés sont exclus de l’entrée IA des enlèvements et les résumés publics refusent les numéros de téléphone.

### Fonctionnement fiable du repli

Sans clé API, si le package OpenAI est indisponible, si l’appel échoue ou si la réponse structurée est invalide, SAVE-US utilise un repli déterministe. Il est identifié explicitement comme logique de démonstration et ne prétend pas vérifier les faits. Il permet aux parcours de signalement, sûreté, modération et ciblage de rester disponibles hors ligne.

## Traçabilité hackathon

L’historique daté des commits du dépôt conserve le travail réalisé pendant la période de soumission : PRD, version anglaise, roadmap, MVP Flask, formulaires, revue structurée GPT-5.6, modération des médias, ciblage, centre de notifications, tests multi-événements et workflow de modération humaine.

SAVE-US est un travail original créé et significativement étendu pour OpenAI Build Week 2026. Les dépendances open source sont utilisées selon leurs licences respectives. Le dépôt ne contient aucune clé OpenAI ni autre identifiant de production.

## Roadmap

Les prochaines étapes sont documentées dans :

- [Roadmap anglaise](RoadMap-SAVE-US_EN.md)
- [Roadmap française](RoadMap-SAVE-US.md)
- [Priorités de soumission anglaises](SAVE_US_Submit_required_EN.md)
- [Priorités de soumission françaises](SAVE_US_Submit_required.md)

Les priorités suivantes sont fiches imprimables/PDF et partage sécurisé (T49–T54), puis tableaux de bord administrateur et vérification hospitalière (T41–T48).

## Licence

Ce projet est distribué sous [licence MIT](LICENSE).
