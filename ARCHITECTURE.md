# Architecture du Projet — Pedagogical AI

> **Version** : 2.0 — Architecture révisée pour la plateforme de préparation pédagogique
> **Dernière mise à jour** : Septembre 2026

---

## 1. Aperçu général

### 1.1 Structure générale

L'application suit une **architecture Flask propre et modulaire** conçue pour la préparation pédagogique d'éveil scientifique (الإيقاظ العلمي) avec génération de contenu prioritaire en arabe.

### 1.2 Principes de conception

- **Arabic-first** : Le contenu pédagogique est prioritairement généré en arabe
- **Modularité** : Système remplaçable pour providers LLM et embeddings
- **Validityité** : Validation complète du contenu pédagogique avant affichage
- **RAG-native** : Pipeline de récupération structuré pour documents de référence
- **Incrementalité** : Développement par phases, pas d'implémentation massive

---

## 2. Structure des répertoires

```
pedagogical_ai/
├── app/
│   ├── __init__.py              # Application factory
│   ├── routes/                  # Point d'entrée web (Blueprints)
│   │   ├── __init__.py
│   │   └── main.py              # Routes principales (Dashboard, Création)
│   ├── models/                  # Entités SQLAlchemy
│   │   ├── __init__.py
│   │   └── *.py                 # User, Course, Lesson, etc.
│   ├── services/                # Logique métier
│   │   ├── __init__.py
│   │   └── *.py                 # Validateur, Planificateur, Générateur
│   ├── ai/                      # Intégration LLM
│   │   ├── __init__.py
│   │   └── provider.py          # GeminiProvider abstraction
│   └── utils/                   # Utilitaires divers
│       ├── __init__.py
│       └── *.py                 # Validation, formatage, utilitaires
│
├── templates/                   # Vue Jinja2 (RTL-aware)
│   ├── base.html                # Héritage avec sidebar navigation française
│   └── dashboard.html           # Page principale (sélecteur de lesson)
│
├── static/                      # Assets statiques
│   ├── css/                     # Style.css (RTL-compatible)
│   └── js/                      # App.js (form validation, UI)
│
├── uploads/                      # Documents importés par les enseignants
├── exports/                      # Fiches PDF/DOCX générées
├── database/                     # Base de données SQLite (futur PostgreSQL)
│   └── app.db
│
├── prompts/                     # Templates de prompts pour les LLM
│   ├── lesson_generation.j2
│   ├── exercise_generation.j2
│   └── validation.j2
│
├── rag/                         # Pipeline RAG
│   ├── __init__.py
│   ├── extractor.py             # PyMuPDF / python-docx
│   ├── embedder.py              # Provider d'embeddings modular
│   ├── retriever.py             # Recherche sémantique ChromaDB
│   └── context_builder.py       # Construction contexte avec métadonnées
│
├── config.py                    # Configuration Flask (dotenv)
├── run.py                       # Point d'entrée (`python run.py`)
├── requirements.txt              # Dépendances PyPI
├── .env.example                 # Variables d'environnement
├── .gitignore                   # Patterns d'ignorance
├── README.md                    # Documentation utilisateur
├── PROJECT_SPEC.md              # Spécification produit (révisée)
├── ARCHITECTURE.md              # Architecture (cette version)
---

## 3. Pile technologique

| Couche | Technologie | Version (actuelle/prochaine) | Notes |
|--------|------------|------------------------------|-------|
| **Web** | Flask | 2.3.3 | Application factory, Blueprints |
| **Database** | SQLAlchemy + SQLite | SQLite (dev) / PostgreSQL (prod) | ORM, migrations futures |
| **Frontend** | Jinja2 + Bootstrap 5 | — | Sidebar RTL-aware, navigation française |
| **AI** | Google Gemini API | Provider abstrait | Pas de clé en dur, .env |
| **RAG** | PyMuPDF, python-docx, ChromaDB | À venir | Extraction → Embeddings → Recherche |
| **Validation** | Validation Python personnalisée | — | Multi-niveaux, auto-corrections |

---

## 4. Architecture logicielle

### 4.1 Cycle de génération de fiche

```
Enseignant demande → Interface (Créer une fiche)
  ↓
Requête validée (matière, niveau, durée, etc.)
  ↓
RAG Retrieval (documents officiels → chunks pertinents)
  ↓
Planificateur pédagogique (harmonise objectifs, durée, niveau)
  ↓
Générateur JSON (structuré via GeminiProvider)
  ↓
Validateur pédagogique (vérifie exactitude, conformité, arabe)
  ↓
Interface résultat (Fiche + Déroulement + Exercices)
```

### 4.2 Architecture RAG (détail)

**Phase d'extraction** (dans `rag/extractor.py`)
- PDF → PyMuPDF → texte brut + métadonnées
- DOCX → python-docx → texte + métadonnées document
- TXT → lecture ligne par ligne
- Nettoyage : suppression des sauts de ligne excessifs, normalisation