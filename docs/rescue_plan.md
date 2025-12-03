# SyncCanvas Rescue Plan

## Goal
Restore basic whiteboard functionality, ensure frontend-backend consistency, and improve code quality.

## Critical Issues
1.  **Whiteboard Broken**: Basic writing/drawing is not working.
2.  **Frontend-Backend Mismatch**: Logic inconsistencies between FE and BE.
3.  **Code Quality**: `ruff` and `pylint` errors need addressing.

## Plan of Action

### Phase 1: Diagnosis & Immediate Fixes (Whiteboard)
- [ ] Analyze `src/ws/sync.py` to understand current WebSocket logic.
- [ ] Analyze Frontend Canvas component (locate file in `frontend/src`).
- [ ] Identify the disconnect (e.g., message format mismatch, connection issues, logic errors).
- [ ] Fix the basic drawing sync.

### Phase 2: Consistency Check
- [ ] Verify data models between Frontend and Backend.
- [ ] Verify API endpoints match Frontend calls.

### Phase 3: Code Quality & Refactoring
- [ ] Run linters (`ruff`, `pylint`) and fix critical errors.
- [ ] Refactor messy code in `src/ws/sync.py` and related files.

### Phase 4: Verification
- [ ] Verify whiteboard drawing works in real-time.
- [ ] Verify persistence (if applicable).
