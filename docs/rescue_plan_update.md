### Next Steps
1.  **Verify Fixes**: User should test if the whiteboard writing now works or if logs provide more insight.
2.  **Frontend-Backend Consistency**: Continue checking for other inconsistencies.
3.  **Code Quality**: Continue addressing linting errors in other files.

## Technical Details

### Backend Fixes (`src/ws/sync.py`)
- Changed `except Exception` to catch specific errors where possible, but kept a broad catch for logging unexpected errors (now properly logged).
- Added `logger.info` and `logger.debug` statements to track room creation and user connections.
- Ensured `room_id` extraction from WebSocket path is robust.

### Frontend Fixes (`frontend/src/lib/yjs.ts`)
- Added listeners for `status`, `connection-error`, and `connection-close` events on the `WebsocketProvider`.
- Added logging to track when connection attempts are made and their outcome.
