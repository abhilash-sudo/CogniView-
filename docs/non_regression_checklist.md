# CogniView Non-Regression Checklist

## Baseline checks
- `GET /` returns 200 and renders library cards.
- `GET /load/<video_id>` returns 200 and video plays.
- `POST /chat` returns JSON with `response`.
- `POST /summary_data`, `POST /flashcards_data`, `POST /mindmap_data` return 200.
- Focus, Gesture, Emotion toggles can switch modes without camera lock.

## API v1 checks
- `GET /health` returns service status payload.
- `POST /api/v1/chat` returns `{ ok, data, error }`.
- `POST /api/v1/summary` returns normalized envelope.
- `POST /api/v1/flashcards` returns normalized envelope.
- `POST /api/v1/mindmap` returns normalized envelope.

## UI checks
- `result.html` controls show active/warn/off states.
- Video dock toggle works and returns to standard layout.
- Matrix, HUD, Binaural buttons reflect on/off state.
