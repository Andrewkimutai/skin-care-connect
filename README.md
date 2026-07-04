#  Skin Care Connect

AI-assisted skin lesion triage that connects users to dermatologists.
Originally built as a Final Year Project (CIT 4299, Dedan Kimathi University
of Technology) — a Streamlit app backed by a ResNet50 transfer-learning
classifier trained on the [HAM10000](https://doi.org/10.7910/DVN/DBW86T) dataset,
with role-based accounts (patient / dermatologist / admin), appointment
booking, and analysis history.

> ⚠️ **This is a research/academic prototype, not a medical device.** See
> [Model performance & limitations](#model-performance--limitations) before
> drawing any conclusions from it.

---

## Features

| Role | Capabilities |
|---|---|
| **User (patient)** | Register/login, upload a skin image for AI classification, view analysis history, book & track appointments |
| **Dermatologist** | Everything a user can do, plus view and respond to all booked appointments |
| **Admin** | Full user management (create, change roles, delete), view all appointments |

- 7-class classification: Actinic Keratosis, Basal Cell Carcinoma, Benign
  Keratosis, Dermatofibroma, Melanoma, Melanocytic Nevi, Vascular Lesion
- Skin-color heuristic pre-filter to reject obviously non-skin uploads
  before running inference
- Confidence-aware recommendations (auto-suggests booking an appointment
  for low-confidence or higher-risk results)
- SQLite persistence, salted PBKDF2 password hashing

---

## Model performance & limitations

The classifier was trained on HAM10000, which is heavily class-imbalanced
(~67% of samples are melanocytic nevi). The held-out evaluation
(`docs/classification_report.txt`) shows why that matters:

| Class | Precision | Recall | F1 |
|---|---|---|---|
| Melanocytic Nevi (nv) | 0.67 | 0.87 | 0.76 |
| Benign Keratosis (bkl) | 0.13 | 0.09 | 0.11 |
| Melanoma (mel) | 0.09 | **0.03** | 0.05 |
| Actinic Keratosis, BCC, Dermatofibroma, Vascular | 0.00 | 0.00 | 0.00 |
| **Overall accuracy** | | | **59.7%** |

**In plain terms:** the model has essentially learned to favor the majority
class. Its recall on Melanoma — the class where a missed case matters most —
is around 3%, meaning it misses the large majority of actual melanoma
images in the evaluation set. Overall accuracy looks moderate mostly
because nevi dominate the dataset.

This repo keeps that report and the confusion matrix (`docs/`) visible
rather than hiding them, because a portfolio project is more credible when
it's honest about where the model needs work. If you want to take this
further, the highest-leverage next step is addressing class imbalance
(class weighting, focal loss, oversampling minority classes, or a
higher-capacity backbone) — see `training/` for the training pipeline.

The app's UI reflects this: results are phrased as model output to review
with a professional, not a diagnosis, and a disclaimer is shown on every
page that touches predictions.

---

## Project structure

```
skin-care-connect/
├── src/
│   ├── app.py          # Streamlit app (entry point)
│   ├── ai_model.py      # Model loading + inference
│   ├── database.py      # SQLite data access layer
│   ├── auth.py           # Salted password hashing
│   └── theme.py          # Shared CSS / UI components
├── models/
│   └── skin_disease_model.h5   # Trained ResNet50-based classifier (~94MB)
├── training/             # Scripts used to build the model (not needed to run the app)
│   ├── data_preprocessing.py
│   ├── organize_ham10000.py
│   ├── model_training.py
│   ├── model_evaluation.py
│   └── requirements-training.txt
├── scripts/
│   └── seed_demo_data.py # Creates demo accounts for a fresh DB
├── docs/                  # Classification report, confusion matrix, training curves
├── sample_images/         # A few HAM10000 test images for quick manual testing
├── .streamlit/config.toml
├── requirements.txt
├── render.yaml
├── Procfile
└── .env.example
```

---

## Running locally

```bash
git clone https://github.com/<your-username>/skin-care-connect.git
cd skin-care-connect

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt

# Optional but recommended: create demo accounts (admin / dermatologist / patient)
python scripts/seed_demo_data.py

streamlit run src/app.py
```

The app will be at `http://localhost:8501`. Demo logins are printed by the
seed script — **change those passwords** before you show this to anyone else,
and never commit `data/app.db`.

---

## Deploying to Render

This repo ships a `render.yaml` (Render "Blueprint") that provisions **both**
the web service and a managed PostgreSQL database automatically:

1. Push this repo to GitHub (see below).
2. In the Render dashboard: **New → Blueprint**, connect the repo. Render
   reads `render.yaml`, creates a free Postgres database named
   `skin-care-connect-db`, and wires its connection string into the web
   service's `DATABASE_URL` environment variable automatically.
3. Or configure manually:
   - Create a **PostgreSQL** instance in Render (New → PostgreSQL).
   - Create a **Web Service** from this repo:
     - Build command: `pip install -r requirements.txt`
     - Start command: `streamlit run src/app.py --server.port $PORT --server.address 0.0.0.0`
     - Runtime: Python 3.11
   - Add an environment variable `DATABASE_URL` on the web service, set to
     your Postgres instance's **Internal Database URL** (found on the
     database's Render dashboard page).
4. After the first deploy, seed demo accounts by running (in the Render
   Shell tab, or locally against the same `DATABASE_URL`):
   ```bash
   python scripts/seed_demo_data.py
   ```
5. **Free Postgres expires 30 days after creation**, with a 14-day grace
   period to upgrade before Render deletes it. Fine for a demo/portfolio
   project — just know the clock is running, and upgrade to a paid instance
   type (or recreate the DB) if you need it to persist longer.
6. The model is loaded from `models/skin_disease_model.h5`, which is
   committed to the repo (~94MB, under GitHub's 100MB hard limit). Cold
   starts on the free tier will take a bit longer because of that — this is
   expected.

### Local development

By default (no `DATABASE_URL` set) the app uses a local SQLite file at
`./data/app.db` — no database server needed. To develop against Postgres
locally instead, set `DATABASE_URL` (see `.env.example`) before running
`streamlit run src/app.py`. The same `src/database.py` code runs against
either backend unchanged.

---


## Tech stack

Streamlit · TensorFlow/Keras (ResNet50 transfer learning) · OpenCV ·
SQLAlchemy (SQLite locally / PostgreSQL in production) · Plotly · Python 3.11

## License

MIT — see [LICENSE](LICENSE).
