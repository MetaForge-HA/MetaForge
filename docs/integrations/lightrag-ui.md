# LightRAG Web UI — Operator Guide

**Status**: Phase 1 (engineer dogfood) · ADR-010 · MET-392 / MET-393

The LightRAG Web UI is a standalone React + Sigma.js single-page app
served by LightRAG's own FastAPI backend. We mount it via
`docker-compose` so engineers can dogfood the L1 knowledge layer
during the MET-346 spike with zero new MetaForge frontend code.

It is **separate from the Kinetic Console**. The integrated
`/knowledge` page in the dashboard arrives in Phase 2; until then,
this UI is the canonical visual surface for the knowledge graph.

---

## What it is

| Component                | Where it lives                              |
|--------------------------|---------------------------------------------|
| LightRAG FastAPI server  | `lightrag-ui` docker-compose service        |
| React + Sigma.js front-end | served at `/`                            |
| Storage backends         | shares the same `pgvector` Postgres the gateway uses, in workspace `lightrag_ui` |
| Embeddings               | local `nomic-embed-text` via ollama sidecar (no API key) |
| LLM                      | local `llama3.2:3b` via ollama sidecar — overridable to Gemini via `.env` |

Documents you ingest through this UI live in their own pgvector
workspace (`lightrag_ui`), separate from the gateway's primary
knowledge data. That's intentional — it keeps engineer experiments
out of the production knowledge stream while still exercising the
real backend.

---

## How to start it

The UI is **opt-in** via a docker-compose profile. The first start
also pulls ~2.5 GB of ollama models (one-time):

```bash
docker compose --profile lightrag up -d
```

That brings up three containers:

| Container                            | Purpose                                  |
|--------------------------------------|------------------------------------------|
| `metaforge-lightrag-ui-1`            | LightRAG FastAPI server + React UI       |
| `metaforge-lightrag-ui-ollama-1`     | Ollama runtime serving embeddings + LLM  |
| `metaforge-lightrag-ui-ollama-bootstrap-1` | One-shot — pulls `nomic-embed-text` and `llama3.2:3b`, then exits |

Once `lightrag-ui` is healthy, open:

```
http://localhost:9621
```

If you set `LIGHTRAG_API_KEY` in your `.env`, the UI will require
that token in the `Authorization: Bearer <key>` header (use the
"Login" panel). Leave it unset for local dev.

### Switching to Gemini for the LLM (optional)

The published LightRAG image only ships the `ollama` and `gemini`
bindings — there is no OpenAI binding. To use Gemini for chat (still
keep ollama for embeddings):

```dotenv
LIGHTRAG_LLM_BINDING=gemini
LIGHTRAG_LLM_MODEL=gemini-2.5-flash
LIGHTRAG_LLM_API_KEY=...your-gemini-api-key...
LIGHTRAG_LLM_HOST=                    # leave blank for gemini
```

To use Gemini for **both** embeddings and the LLM:

```dotenv
LIGHTRAG_EMBEDDING_BINDING=gemini
LIGHTRAG_EMBEDDING_MODEL=text-embedding-004
LIGHTRAG_EMBEDDING_DIM=768
LIGHTRAG_EMBEDDING_API_KEY=...your-gemini-api-key...
LIGHTRAG_EMBEDDING_HOST=

LIGHTRAG_LLM_BINDING=gemini
LIGHTRAG_LLM_MODEL=gemini-2.5-flash
LIGHTRAG_LLM_API_KEY=...your-gemini-api-key...
LIGHTRAG_LLM_HOST=
```

Optional UI-lock-down env vars (add to your `.env` if needed):

```dotenv
LIGHTRAG_API_KEY=                     # leave blank for local dev
LIGHTRAG_UI_PORT=9621                 # override the host port mapping
```

---

## What each tab does

| Tab          | Purpose                                                                   |
|--------------|---------------------------------------------------------------------------|
| **Graph**    | Interactive knowledge-graph canvas. Click a node to see its neighbours and the documents it appears in. |
| **Documents**| Upload markdown / PDF / plain-text files; see chunk counts, processing status, and last-modified time. |
| **Chat**     | Streamed retrieval testing. Query → see the answer, citations, and the KG canvas highlight matched entities. Requires LLM env vars set. |
| **Swagger**  | `/docs` — full FastAPI route reference. Useful for poking the underlying API by hand. |

---

## When to use it vs the future `/knowledge` page

| Use this UI when…                                              | Use the integrated `/knowledge` page when… |
|----------------------------------------------------------------|--------------------------------------------|
| You're iterating on chunking / embedding / extraction logic    | You're an end-user reviewing your own design's knowledge |
| You need to inspect the raw knowledge graph (entities, edges)  | Phase 2 lands the embedded view (date TBD) |
| You're debugging a poor retrieval result                        | You want fragment search alongside the rest of the dashboard's controls |
| You're verifying MET-346 spike adoption criteria                | —                                          |

---

## MET-346 spike adoption checklist

Use this UI to check off each criterion in the spike:

- [ ] **Ingest works** — drag a markdown file into Documents → it
  reaches `processed` status with a non-zero chunk count
- [ ] **Graph extraction works** — open Graph → see entities + edges
  derived from the document (LLM-driven; needs an LLM key configured)
- [ ] **Vector retrieval works** — Chat with a phrase that appears
  verbatim in your doc → answer references the doc with a citation
- [ ] **Hybrid retrieval works** — Chat with a paraphrase → answer still
  surfaces the right doc (graph + vector working together)
- [ ] **Citation chain is complete** — every chat answer shows
  `source_path` and chunk index, matching the values stored in
  `knowledge_entries` (verify by `psql` or via the gateway's
  `/api/v1/knowledge/search`)

If any criterion fails, file a P1 ticket against MET-346 with a
screenshot + the matching `lightrag-ui` container log slice.

---

## Cross-references

- [ADR-010 — Knowledge Visualization](https://github.com/MetaForge-HA/MetaForge-Planner/blob/main/docs/architecture/adr-010-knowledge-visualization.md) — the architectural decision behind this Phase 1 / Phase 2 split
- [MET-346](https://linear.app/metaforge/issue/MET-346) — the L1 KnowledgeService spike this UI dogfoods
- [MET-392](https://linear.app/metaforge/issue/MET-392) — the docker-compose mount task
- [MET-393](https://linear.app/metaforge/issue/MET-393) — this doc
- [`docs/architecture/knowledge-ingestion-playbook.md`](../architecture/knowledge-ingestion-playbook.md) — what fields LightRAG's chunking pipeline expects
