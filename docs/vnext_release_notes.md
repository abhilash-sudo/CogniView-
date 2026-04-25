# CogniView vNext Upgrade Notes

## Highlights
- Introduced modular cognitive frontend under `static/js/`.
- Added unified camera lifecycle controller for Focus/Gesture/Emotion.
- Added API v1 compatibility layer with normalized envelopes.
- Added AI task-based model routing and short-lived response cache.
- Added `/health` diagnostics endpoint.
- Improved DB connection lifecycle handling with context manager helpers.

## Rollback Plan
1. Revert `server.py`, `services/ai_service.py`, `services/db_service.py`, and `templates/result.html`.
2. Remove `static/js/cognitive/*` and `static/js/ui/*`.
3. Restart Flask server and validate `GET /` and `/load/<id>`.

## Follow-up (Post Week-1)
- Migrate templates to React + TypeScript incrementally.
- Move API v1 handlers into Flask blueprints.
- Replace in-memory AI cache with persistent cache (Redis or SQLite table).
- Add automated browser E2E checks for cognitive controls.
