# 🏠 Luxarmonie Hub

Application de gestion des prix pour Luxarmonie - Modification en masse des prix sur tous les marchés Shopify.

![Luxarmonie Hub](https://via.placeholder.com/800x400/a98977/ffffff?text=Luxarmonie+Hub)

## ✨ Fonctionnalités

- **Modification de prix en masse** - Tous les marchés en quelques clics
- **Sélection flexible** - Par pays (1, plusieurs, ou tous) et par produit
- **Règles automatiques** - TVA, taux de change, terminaisons psychologiques par culture
- **Prévisualisation** - Voir tous les changements avant d'appliquer
- **Interface premium** - Design Luxarmonie (terracotta, noir, blanc)

## 🛠️ Stack Technique

| Composant | Technologie |
|-----------|-------------|
| Frontend | React + Tailwind CSS |
| Backend | Python FastAPI |
| API | Shopify GraphQL Admin |
| Déploiement | Railway |

## 📋 Prérequis

1. **Node.js** 18+ et **npm**
2. **Python** 3.11+
3. **Compte Railway** (gratuit)
4. **App Shopify** avec les scopes requis

## 🔐 Configuration Shopify

### Créer une App Privée

1. Va dans **Shopify Admin** → **Settings** → **Apps and sales channels**
2. Clique sur **Develop apps** → **Create an app**
3. Nomme l'app "Luxarmonie Hub"
4. Configure les **API scopes** :
   - `read_products`, `write_products`
   - `read_markets`, `write_markets`
   - `read_price_rules`, `write_price_rules`
5. Installe l'app et copie le **Access Token**

## 🚀 Déploiement sur Railway

### Étape 1 : Préparer le repo GitHub

```bash
# Clone ou crée un nouveau repo
git clone https://github.com/ton-username/luxarmonie-hub.git
cd luxarmonie-hub

# Copie tous les fichiers du projet ici
# Puis push
git add .
git commit -m "Initial commit"
git push origin main
```

### Étape 2 : Déployer sur Railway

1. Va sur [railway.app](https://railway.app) et connecte-toi avec GitHub
2. Clique sur **New Project** → **Deploy from GitHub repo**
3. Sélectionne `luxarmonie-hub`

### Étape 3 : Configurer le Backend

1. Railway va créer automatiquement un service
2. Clique sur le service → **Settings** → **Root Directory** → `/backend`
3. Va dans **Variables** et ajoute :
4. 
   ```
   SHOPIFY_SHOP_DOMAIN=luxarmonie.myshopify.com
   SHOPIFY_ACCESS_TOKEN=shpat_xxxxx
   ```
5. Railway va déployer automatiquement

### Étape 4 : Configurer le Frontend

1. Clique sur **New** → **GitHub Repo** → même repo
2. **Settings** → **Root Directory** → `/frontend`
3. **Build Command** : `npm install && npm run build`
4. **Start Command** : `npm run preview -- --host --port $PORT`
5. Ajoute la variable :
   ```
   VITE_API_URL=https://ton-backend.railway.app
   ```

### Étape 5 : Générer les domaines

1. Pour chaque service, va dans **Settings** → **Networking**
2. Clique sur **Generate Domain**
3. Note les URLs

## 💻 Développement Local

### Backend

```bash
cd backend

# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt

# Configurer les variables
cp ../.env.example .env
# Édite .env avec tes credentials

# Lancer le serveur
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend

# Installer les dépendances
npm install

# Lancer en mode dev
npm run dev
```

Accède à `http://localhost:3000`

## 📁 Structure du Projet

```
luxarmonie-hub/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── routers/
│   │   │   ├── pricing.py       # API pricing
│   │   │   ├── markets.py       # API marchés
│   │   │   └── products.py      # API produits
│   │   ├── services/
│   │   │   ├── shopify.py       # Client Shopify GraphQL
│   │   │   └── pricing_engine.py # Moteur de calcul
│   │   └── config/
│   │       └── countries.py     # Config pays (terminaisons, TVA...)
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Sidebar.jsx
│   │   │   └── PricingModule.jsx
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── tailwind.config.js
│   └── package.json
│
├── railway.toml
└── README.md
```

## 🎨 Design System

| Élément | Valeur |
|---------|--------|
| **Police** | Inter |
| **Titres** | Semi Bold, -4% letter-spacing |
| **Texte** | Regular, -3% letter-spacing |
| **Terracotta** | `#a98977` |
| **Noir** | `#000000` |
| **Blanc** | `#ffffff` |

## 🔧 Configuration des Pays

Les terminaisons de prix sont configurées dans `backend/app/config/countries.py` :

| Type | Pays | Exemple |
|------|------|---------|
| `.99` | France, USA, UK | 98.99€ |
| `.95` | Allemagne, Autriche | 98.95€ |
| `.00` | Brésil, Italie, HK | 99.00€ |
| `entier 9` | Arabie Saoudite, UAE | 349 SAR |
| `milliers` | Chili, Colombie | 90,000 CLP |

## 📝 API Endpoints

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/markets` | GET | Liste des marchés |
| `/api/products` | GET | Recherche produits |
| `/api/pricing/config` | GET | Configuration pricing |
| `/api/pricing/preview` | POST | Prévisualiser les prix |
| `/api/pricing/apply` | POST | Appliquer les prix |

## 🆘 Support

Des questions ? Contacte-nous sur Slack ou ouvre une issue sur GitHub.

---

**Luxarmonie Hub** - Made with ❤️ for Luxarmonie
