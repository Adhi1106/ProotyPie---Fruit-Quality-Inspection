# Frontend work

## Changed
- Revamped dashboard messaging and status treatment while preserving existing inspect, storage, spotlight, and chat contracts.
- Added same-origin API default and Next rewrite to `BACKEND_ORIGIN` (default `http://127.0.0.1:8017`).
- Added `/api/health` readiness display with honest TensorFlow/Gemini/local-reference distinctions.
- Added accessible keyboard-operated upload dropzone, explicit analysis states, model-confidence safety disclaimer, JSON export, and print styling.
- Added separate **Fruit classification lab** mode calling `/api/classify`; results state the model scope and never present fruit-type classification as freshness or safety.
- Existing chat persistence remains in version-local browser storage.

## Test-first evidence
- Added `frontend/tests/frontend-behavior.mjs` before implementation.
- Initial run failed on same-origin API assertion as expected.
- Final: `node tests/frontend-behavior.mjs` passed.
- Final: `npm run lint` passed with zero warnings.
- Final: `npm run build` passed (Next 16.2.10). Only warning is Next's existing multiple-lockfile workspace-root inference.

## Files
- `frontend/app/page.tsx`
- `frontend/app/globals.css`
- `frontend/lib/api.ts`
- `frontend/types.ts`
- `frontend/next.config.mjs`
- `frontend/tests/frontend-behavior.mjs`
