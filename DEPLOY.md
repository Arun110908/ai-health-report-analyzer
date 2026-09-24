# Deploy from an existing repository

The included `Dockerfile` builds the React dashboard and FastAPI backend into
one service. The container serves the dashboard at `/` and API routes under
`/api`, which avoids CORS and separate-domain configuration.

## Add this project to the existing repository

Copy the project files (including hidden files) into the repository root, then
commit and push them:

```bash
cd /path/to/existing-repository
cp -R /path/to/ai-health-report-analyzer/. .
git add .
git commit -m "Add AI health report analyzer"
git push
```

Do not commit real reports, `.env` files, `frontend/node_modules`, generated
`backend/models/*.joblib`, or generated `backend/data/*.csv`.

## Run locally with Docker

```bash
docker compose up --build
```

Open `http://localhost:8000`. The API health endpoint is
`http://localhost:8000/health`.

## Deploy on any Docker-capable host

1. Connect the existing Git repository to the hosting provider.
2. Choose **Dockerfile** / **Docker** as the build method.
3. Set the service port to `8000`, or let the platform provide `PORT`.
4. Add `ANTHROPIC_API_KEY` as a secret only if Claude-generated text is
   desired. Without it, the application uses the included rule-based path.
5. The Docker build generates and trains the LightGBM + KNN model from a
   synthetic academic dataset. It is intentionally non-clinical, but makes the
   SHAP explanation panel available immediately after deployment. To disable
   it, set Docker build argument `TRAIN_DEMO_RISK_MODEL=false`.
6. Do not enable public logging of uploads or request bodies; lab reports may
   contain sensitive health information.

The server's start command is already in the Dockerfile. No separate frontend
deployment or `VITE_API_BASE` is needed: the dashboard uses same-origin `/api`
requests in the container.
