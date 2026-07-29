# Infrastructure

How this project is deployed and what runs where. Written so you can reproduce the setup for
your own instance — every identifier here is a placeholder, because this repo deliberately names
no running deployment (see [Why no URLs](#why-no-urls-in-this-repo)).

## Topology

```
browser
  ├─ <your-ui>.pages.dev            static assets, Cloudflare CDN
  │    └─ /api/*                    Cloudflare Pages Function (same-origin proxy)
  │         └─ [edge cache, 5 min]
  │              └─ Cloud Run       FastAPI container, scale-to-zero
  │                   └─ Open-Meteo forecast / ensemble / geocoding APIs
  ├─ view.eumetsat.int              WMS satellite tiles, straight from the browser
  └─ basemaps.cartocdn.com          CARTO Voyager basemap tiles
```

Only the `/api` path touches Google Cloud. Satellite imagery and basemap tiles are fetched by the
browser directly from EUMETSAT and CARTO, so they cost you nothing and need no proxying.

The UI never calls the backend cross-origin: in development Vite's `server.proxy` forwards
`/api`, in production the Pages Function does. **CORS is therefore never exercised**, and no
backend URL is baked into the JavaScript bundle.

## The API — Google Cloud Run

A single stateless, keyless container built from the repo [`Dockerfile`](../Dockerfile). No
database, no persistent state, no secrets — it holds nothing worth protecting, which is why it
can run public and scale to zero.

```bash
gcloud run deploy <your-service> --source . --region <your-region> \
  --allow-unauthenticated --max-instances 1 --timeout 20s \
  --set-env-vars ALLOWED_ORIGINS=https://<your-ui-origin>
```

`--source` makes Cloud Build build the Dockerfile and push to an Artifact Registry repo
(`cloud-run-source-deploy`, created on first deploy). Defaults otherwise: 1 vCPU, 512 MiB,
concurrency 80, startup CPU boost.

**`--max-instances` and `--timeout` are cost controls, and they are pinned in
[`ci-cd.yml`](../.github/workflows/ci-cd.yml)** rather than set by hand, so a service recreated
from scratch cannot silently come back with the defaults (100 instances, 300 s).

## Automated deploys — GitHub Actions + Workload Identity Federation

Push to `main` → tests → deploy. Authentication is **keyless**: no service-account JSON key
exists anywhere. GitHub mints an OIDC token, and a Workload Identity Pool exchanges it for
short-lived Google credentials.

Two things must both name your repository, or the deploy cannot mint credentials:

```bash
# 1. the provider only trusts tokens from your repo
gcloud iam workload-identity-pools providers update-oidc <provider> \
  --project=<project> --location=global --workload-identity-pool=<pool> \
  --attribute-condition="assertion.repository=='<owner>/<repo>'"

# 2. that repo may impersonate the deploy service account
gcloud iam service-accounts add-iam-policy-binding <deployer>@<project>.iam.gserviceaccount.com \
  --project=<project> --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/<project-number>/locations/global/workloadIdentityPools/<pool>/attribute.repository/<owner>/<repo>"
```

**Renaming the GitHub repo breaks deploys** until both are updated.

Deployer roles: `run.admin`, `cloudbuild.builds.editor`, `artifactregistry.writer`,
`storage.admin`, `iam.serviceAccountUser`.

Deploy targets come from repository secrets — see
[`api/README.md`](../api/README.md#automated-deploys-github-actions) for the full list and the
`gh secret set` commands.

## The UI — Cloudflare Pages

Static direct upload, no Git integration:

```bash
nvm use && npm run build
npx wrangler pages deploy dist --project-name=<your-project>
```

`wrangler` uploads `dist/` and compiles the sibling `functions/` directory into the Pages
Function that serves `/api/*`. Add `--branch=<name>` to get a preview deployment on its own URL.

The proxy needs the backend URL as a secret, **per environment**:

```bash
npx wrangler pages secret put API_ORIGIN --project-name=<your-project>
npx wrangler pages secret put API_ORIGIN --project-name=<your-project> --env preview
```

Without it, `/api/*` returns 503. The Function rejects non-GET, forwards `/api/foo` to
`${API_ORIGIN}/foo`, and caches successful responses for 5 minutes at the edge — so repeat
queries never reach Cloud Run.

Two behaviours worth knowing if you modify it: Cloudflare does **not** cache Function responses
from `Cache-Control` alone (you must use the Cache API explicitly), and a new deployment
propagates unevenly across colos for a minute or two, during which the same URL can alternate
between old and new. Both cost real debugging time.

## Cost

Everything sits in free tiers under normal use: Cloud Run scales to zero, Pages is free for
static hosting and Functions, and Open-Meteo/EUMETSAT/CARTO are free at this volume.

The exposure is an unauthenticated public endpoint. Bounding it:

- **`--max-instances`** is the real ceiling — it caps how much compute can ever run at once.
- **The edge cache** absorbs repeat traffic before it reaches Cloud Run.
- **A billing budget alerts but cannot stop spend.** GCP has no hard cap. A true kill switch
  needs budget → Pub/Sub → a function that detaches the billing account.

## Why no URLs in this repo

The Cloud Run URL is derivable from project number + service + region, so naming any of them
here would expose the deployment. They live in repository secrets instead, and the docs use
placeholders. This keeps the instance out of code search and scrapers — but note it does **not**
hide it from anyone using the deployed site, since the proxy's own origin is public. The point is
reducing casual discovery, not secrecy.

## Hardening not done here

Deliberate gaps, listed so they are choices rather than oversights:

- **Runtime service account.** Cloud Run defaults to the compute SA, which typically holds
  project-wide `roles/editor`. This app needs no GCP permissions at all — deploy with
  `--service-account=<sa>` pointing at a dedicated SA with no role bindings.
- **The backend is reachable directly** by anyone who learns its URL. Closing that means
  `--no-allow-unauthenticated` plus an ID token minted in the Worker.
- **No effective rate limiting.** Per-isolate counters in a Pages Function do not accumulate
  across Cloudflare's isolates. Real options are Durable Objects or a custom domain with a WAF
  rate-limiting rule.
- **Single region, single instance** — no redundancy.
