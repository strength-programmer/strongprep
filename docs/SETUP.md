# Setup and integration configuration

Read for scaffolding, dependencies, credential setup, or enabling live services. Initial local demo must work without keys.

Use the following stack for this build. The initial demo is defined in section 0; external service connections are enabled as their credentials and data permissions become available. Official documentation is listed in sources S7–S14. This selection is a practical project decision rather than a comparison proving these vendors are best.

| Layer | Selected tool/service | Purpose and first-build status |
| --- | --- | --- |
| Frontend | Next.js, React, TypeScript [S7] | Athlete screens; implement immediately |
| Backend | Python, FastAPI, Pydantic, Uvicorn [S8] | Validated API, calculations, and integration calls; implement immediately |
| Persistence | SQLAlchemy with SQLite for the local demo; Supabase PostgreSQL for live mode [S9] | Persist athlete data, results, and versioned plans; provide schema migrations |
| Authentication | Supabase Auth [S10] | Real accounts in live mode; isolated fixed identity in local demo only |
| AI generation | Claude API through the `anthropic` Python SDK [S11] | Structured extraction/explanation/planning; mock provider first and configurable live adapter |
| Competition search | Tavily Search API [S12] | Find candidate source URLs; interface/mock first, live integration later |
| Page extraction | Firecrawl API [S13] | Read permitted pages for structured extraction; interface/mock first, live integration later |
| Orchestration | Plain Python workflow initially; LangGraph when useful [S6] | Coordinate validated steps without an unnecessary initial framework dependency |
| Knowledge | Structured exercise/template catalog and source excerpts | Sample catalog for demo; reviewed material for live training recommendations |
| Hosting | Vercel for Next.js; Render for FastAPI [S14] | Optional deployment after local build verification |
| Long-running jobs | Persistent job records and a worker when required | Later imports/research; bounded mock steps may run synchronously in the initial demo |

**Claude Code is the development assistant. The Claude API is the AI integration used by the running app.** The deployed application must function independently of an open Claude Code session.

Search and extraction have different jobs: Tavily finds pages; Firecrawl reads selected pages. Neither supplies a complete, verified strongman results dataset. Historical results still require a suitable permitted source, and exercise guidance still requires reviewed content.

### Local project organization

```text
strongprep/
  frontend/                 Next.js app, frontend tests, package.json
  backend/
    app/
      api/                  FastAPI routes and auth dependencies
      schemas/              Validated input/output models
      models/               Persistent entities
      services/             Assessments, benchmarks, plans, and versioning
      integrations/         Claude, Tavily, Firecrawl, and mock adapters
      data/                 Labeled fixtures and template catalog
    migrations/             Schema migrations
    tests/                  Domain and integration tests
    pyproject.toml          Python dependencies
    .env.example
  README.md                 Windows CMD setup, launch, and verification
```

Frontend requests go to FastAPI. The backend owns assessment calculations and sensitive integration calls. In live mode, validate Supabase-issued access tokens before accessing athlete records, derive the owner from the verified identity, and enforce ownership on every private read/write. Apply appropriate row-level policies wherever Supabase exposes database tables directly. Never accept a client-supplied athlete owner as authorization.

### Configuration and credentials

Provide the following example variables with placeholders, not working secrets. These are application configuration names; implement and document them consistently.

| Location | Variables | Usage |
| --- | --- | --- |
| Backend | `APP_MODE=demo`, `DATABASE_URL=sqlite:///./strongprep-demo.db` | Default persistent local demo |
| Backend, live AI | `ANTHROPIC_API_KEY`, `CLAUDE_MODEL`, `AI_PROVIDER=claude` | Configured model integration; demo uses `AI_PROVIDER=mock` |
| Backend, later search | `TAVILY_API_KEY`, `FIRECRAWL_API_KEY` | Optional live discovery/extraction; absent keys must not break manual entry |
| Backend, live database/auth | `DATABASE_URL`, `SUPABASE_URL` | Target PostgreSQL connection and trusted auth project; document verification configuration |
| Frontend | `NEXT_PUBLIC_API_BASE_URL` | Backend URL; local default `http://localhost:8000` |
| Frontend, live auth | `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Browser-safe project connection for login |
| Backend | `CORS_ALLOWED_ORIGINS` | Explicit permitted frontend origins; local default `http://localhost:3000` |

Store real secrets outside source control. Claude, Tavily, Firecrawl, database passwords, and any privileged Supabase keys belong on the server, never in `NEXT_PUBLIC_` variables. A Supabase publishable key is intended for client use; authorization policies remain necessary. Make model selection configurable and check current SDK documentation rather than inventing a model identifier or freezing outdated API examples.

### Dependencies and account setup

Use a project-specific Python environment and Node.js for frontend tooling. Record compatible versions in the repository. Suggested backend packages are `fastapi`, `uvicorn`, `pydantic-settings`, `sqlalchemy`, `alembic`, `anthropic`, `httpx`, and the JWT-verification dependency required by the chosen authentication approach. Add a PostgreSQL driver for live mode and `pytest` for backend verification. Use official provider SDKs or documented HTTP interfaces for later search/extraction.

For live operation, the owner will create a Supabase project and obtain Claude API credentials. Tavily and Firecrawl accounts are needed when their live adapters are enabled. Hosting accounts are needed only for deployment. Document this checklist and each integration's status without blocking the mock demo on missing credentials.

A vector database is optional. Athlete records, dates, weights, and results belong in structured storage. Add semantic retrieval only when a substantial approved knowledge collection justifies it.

Build notes: the backend `CORS_ALLOWED_ORIGINS` default is `http://localhost:3000,http://127.0.0.1:3000`; `backend/requirements-lock.txt` is the pinned install set; a Supabase JWT is verified with `SUPABASE_JWT_SECRET` if set, otherwise via the project's JWKS endpoint.

Research labels S6–S14 resolve in docs/research/SOURCES.md. For module ownership and canonical API names use ARCHITECTURE and CONTRACTS rather than the layout example above.
