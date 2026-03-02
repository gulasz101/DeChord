# Portless Local Dev Design

## Summary
Adopt [Portless](https://github.com/vercel-labs/portless) as the default local development entrypoint for DeChord web app services to avoid backend/frontend port collisions while keeping stable URLs for browser access and proxying.

## Approved Scope
- Include: local developer workflows (`make up`, `make down`, `make status`, `make logs`), app runtime config, and README docs.
- Exclude: CI flows and CI-specific scripts.

## Target URLs
- Frontend: `http://dechord.localhost:1355`
- Backend: `http://api.dechord.localhost:1355`

## Architecture
- Frontend dev server runs under `portless dechord ...`.
- Backend FastAPI dev server runs under `portless api.dechord ...`.
- Portless allocates real free ports and routes requests via a stable virtual host on proxy port `1355`.
- Vite API proxy targets `http://api.dechord.localhost:1355` with `changeOrigin: true` to avoid host-loop routing issues.

## Makefile Direction
- Make Portless-backed startup the default `make up` path.
- Preserve existing tmux lifecycle commands, but run app commands via Portless wrappers.
- Add explicit Portless helper targets for starting/stopping the proxy and listing routes.

## Documentation Direction
- Document Portless as a prerequisite (`npm install -g portless`).
- Replace localhost:5173/8000 local start URLs with stable Portless URLs.

## Verification Direction
- Add a frontend test that verifies Vite proxy target uses `api.dechord.localhost:1355`.
- Run full local verification after implementation, including reset workflow before final handoff.

## Design Tasks
- [x] Explore project context and existing startup/runtime scripts.
- [x] Clarify scope and domain naming with user (`dechord` and `api.dechord`).
- [x] Evaluate integration approaches and select recommended option.
- [x] Produce approved design for runtime/config, commands, docs, and verification.
