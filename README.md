# SyncCanvas

SyncCanvas is a collaborative Excalidraw whiteboard with FastAPI, Yjs/CRDT sync, room history, and a spec-first AI diagram pipeline.

## What It Does

- Realtime multi-user canvas sync with Yjs over WebSocket
- Room-based persistence and version history backed by SQLite
- AI chat sidebar with streaming tool progress
- Spec-first managed diagrams for paper-style figures
- Local editing that can write top-level managed changes back into diagram spec/state

## Current Architecture

### Backend

- `main.py`: app entrypoint
- `src/routers/ai.py`: AI request and stream routes
- `src/routers/rooms.py`: rooms, history, and diagram routes
- `src/routers/config.py`: model/config management routes
- `src/ws/sync.py`: Yjs websocket sync
- `src/db/ystore.py`: Yjs update buffering and persistence
- `src/agent/diagram/`: spec-first managed diagram models, render, storage, service

### Frontend

- `frontend/src/components/canvas/Canvas.tsx`: main Excalidraw canvas shell
- `frontend/src/components/ai/AISidebar.tsx`: AI sidebar container
- `frontend/src/components/ai/AgentMode.tsx`: AI chat + planning + diagram preview flow
- `frontend/src/lib/yjs.ts`: Excalidraw/Yjs bindings and managed reverse-sync

## Managed Diagram Flow

The current managed diagram pipeline is:

`prompt -> DiagramSpec -> render -> Y.Doc diagram maps -> managed reverse-sync`

Managed diagram metadata is stored alongside normal elements in the same room document:

- `diagram_specs`
- `diagram_manifests`
- `diagram_state`
- `diagram_index`

Top-level managed objects can write back to spec. More free-form edits fall back to `semi_managed`.

## Local Development

### Backend

```bash
uv run python main.py
```

The backend serves the API and built frontend assets.

### Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

### Frontend build

```bash
cd frontend
pnpm build
```

## Validation Commands

### Backend

```bash
uv run python -m compileall main.py src
uv run pytest tests -q
```

### Frontend

```bash
cd frontend
pnpm exec tsc --noEmit --pretty false
pnpm build
pnpm test
```

## Notes

- The current roadmap is focused on making managed diagrams stable and maintainable before expanding more diagram families.
- `docs/managed-diagram-flow.md` and `docs/reverse-sync-rules.md` describe the current spec-first behavior in more detail.
