# Spécification du Projet — Pedagogical AI

> **Version** : 2.0 — Direction révisée (Plateforme de préparation pédagogique)
> **Dernière mise à jour** : Septembre 2026
> **Public cible** : Enseignants du primaire (Éveil scientifique / الإيقاظ العلمي)

---

## 1. VISION PRODUIT

### 1.1 Définition

Pedagogical AI est une **plateforme IA de préparation pédagogique** destinée aux enseignants du primaire, spécialisée initialement dans :

**الإيقاظ العلمي** (Éveil scientifique)

Le projet n'est **pas** un chatbot. C'est un outil de préparation de cours complet.

### 1.2 Langue

| Rôle | Langue |
|------|--------|
| Contenu pédagogique généré | العربية الفصحى (priorité absolue) |
| Interface navigation | Français (initialement) |
| Support futur | Français, Anglais |

### 1.3 Workflow principal

```
Dashboard
  ↓
Créer une fiche
  ↓
Saisie enseignant :
  - Matière : الإيقاظ العلمي
  - Niveau : س1 / س2 / س3 / س4 / س5 / س6 ابتدائي
  - Sujet / Leçon
  - Durée
  - Objectifs d'apprentissage
  - Difficulté
  - Langue
  - Documents de référence
  ↓
Bouton : "حضّر لي الدرس"
  ↓
RAG → Planificateur → Générateur → Validateur
  ↓
Fiche pédagogique complète
```
# Spécification du Projet — Pedagogical AI

> **Version** : 2.0 — Direction révisée (Plateforme de préparation pédagogique)
> **Dernière mise à jour** : Septembre 2026
> **Public cible** : Enseignants du primaire (Éveil scientifique / الإيقاظ العلمي)

---

## 1. VISION PRODUIT

### 1.1 Définition

Pedagogical AI est une **plateforme IA de préparation pédagogique** destinée aux enseignants du primaire, spécialisée initialement dans :

**الإيقاظ العلمي** (Éveil scientifique)

Le projet n'est **pas** un chatbot. C'est un outil de préparation de cours complet.

### 1.2 Langue

| Rôle | Langue |
|------|--------|
| Contenu pédagogique généré | العربية الفصحى (priorité absolue) |
| Interface navigation | Français (initialement) |
| Support futur | Français, Anglais |

### 1.3 Workflow principal

```
Dashboard
  ↓
Créer une fiche
  ↓
Saisie enseignant :
  - Matière : الإيقاظ العلمي
  - Niveau : س1 / س2 / س3 / س4 / س5 / س6 ابتدائي
  - Sujet / Leçon
  - Durée
  - Objectifs d'apprentissage
  - Difficulté
  - Langue
  - Documents de référence
  ↓
Bouton : "حضّر لي الدرس"
  ↓
RAG → Planificateur → Générateur → Validateur
  ↓
Fiche pédagogique complète

---

## 2. SORTIE PRINCIPALE — الجذاذة

La génération produit une **fiche pédagogique complète** (21 sections) :

1. **عنوان الدرس** — Titre de la leçon
2. **المادة** — Matière (الإيقاظ العلمي)
3. **المستوى الدراسي** — Niveau scolaire
4. **المدة الزمنية** — Durée demandée
5. **الكفاءة المستهدفة** — Compétence ciblée
6. **الأهداف التعليمية** — Objectifs d'apprentissage
7. **المكتسبات السابقة** — Acquis préalables
8. **الوسائل التعليمية** — Moyens pédagogiques
9. **المفاهيم والمصطلحات الأساسية** — Concepts & termes clés
10. **وضعية الانطلاق** — Situation de départ
11. **مراحل بناء التعلمات** — Phases de construction
12. **أنشطة المعلم** — Activités enseignant
13. **أنشطة المتعلم** — Activités apprenant
14. **الأسئلة التوجيهية** — Questions guidées
15. **التجارب أو الأنشطة العلمية** — Activités scientifiques
16. **الأمثلة** — Exemples concrets
17. **التقويم التكويني** — Évaluation formative
18. **التقويم النهائي** — Évaluation sommative
19. **الدعم والعلاج** — Soutien & remédiation
20. **خلاصة الدرس** — Synthèse
21. **نشاط أو واجب منزلي** — Devoirs

> ⚠️ La fiche doit être **pratique et immédiatement utilisable**, pas théorique.

---

## 3. DÉROULEMENT DE SÉANCE — "كيف أقدّم هذا الدرس؟"

Le système génère un **scénario de classe détaillé** :

```
PHASE 1 — التمهيد (5 min)
  ✅ Action enseignant : ...
  ✅ Action élève : ...
  ✅ Questions : ...
  ✅ Réponses attendues : ...

PHASE 2 — وضعية الانطلاق
  ✅ Action enseignant : ...
  ✅ Action élève : ...

PHASE 3 — بناء التعلمات
  ✅ ...

PHASE 4 — التقويم
  ✅ ...

PHASE 5 — الخلاصة
  ✅ ...
```

**Contrainte** : La durée totale respecte la durée demandée par l'enseignant.

---

## 4. GÉNÉRATEUR D'EXERCICES

### 4.1 Types supportés

- أسئلة مباشرة
- صح أو خطأ
- أكمل الفراغ
- صل بسهم
- صنّف
- اختر الإجابة الصحيحة
- أسئلة قصيرة
- وضعيات تطبيقية
- أنشطة ملاحظة
- أنشطة علمية (quand approprié)

### 4.2 Chaque exercice contient

- Question
- Instructions
- Réponse attendue
- Correction détaillée
- Objectif d'apprentissage
- Difficulté

### 4.3 Règle fondamentale

Les exercices n'utilisent **que** les concepts enseignés dans la leçon générée.

---

## 5. ÉVALUATION

Génération d'une section d'évaluation avec :

- Questions
- Corrections
- Explications
- Objectifs d'apprentissage
- Difficulté

**Interdiction** : Questions ambiguës.

---

## 6. BASE DE CONNAISSANCES

### 6.1 Types de documents (3 catégories)

| Catégorie | Description |
|-----------|-------------|
| **Documents officiels** | Programmes officiels, manuels, guides enseignants |
| **Documents enseignants** | Documents uploadés par l'enseignant |
| **Sources web** | Sources éducatives fiables |

### 6.2 Formats supportés (futur)

- PDF
- DOCX
- TXT
- Sources web

### 6.3 Priorisation

L'IA privilégie les **documents de référence officiels**.

---

## 7. SYSTÈME RAG (Retrieval-Augmented Generation)

### 7.1 Pipeline

```
Requête enseignant
  ↓
Récupération documents
  ↓
Chunks pertinents
  ↓
Construction contexte
  ↓
Gemini
  ↓
Génération structurée
  ↓
Validation
  ↓
Résultat final
```

### 7.2 Stack technique (initiale)

- **Extraction** : PyMuPDF, python-docx
- **Stockage vectoriel** : ChromaDB
- **Embeddings** : Modular (remplaçable)
- **Architecture** : Modulaire pour remplacement futur du provider d'embeddings

### 7.3 Métadonnées par chunk

```json
{
  "document_id": "uuid",
  "filename": "book.pdf",
  "source_type": "official|teacher_upload|web",
  "subject": "الإيقاظ العلمي",
  "educational_level": "س5",
  "language": "ar",
  "chapter": "النباتات",
  "page_number": 42,
  "source_url": null
}
```

### 7.4 Citations sources

Quand la leçon utilise des documents de référence :
```
Source : كتاب الإيقاظ العلمي - السنة الخامسة
Page : 42
```

Si l'info n'est pas dans les sources disponibles :
> ⚠️ « Cette information n'est pas disponible dans les sources fournies. »

---