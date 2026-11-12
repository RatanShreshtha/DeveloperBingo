# Frontend

Vue app for DeveloperBingo. See the root `README.md` for how to run and test it.

## App and routes

`src/application.ts` creates the Vue app with Pinia and the router. It accepts a
router history so tests can use memory history. Routed pages are lazy-loaded;
their URLs and the development proxy remain unchanged.

## Game session

The host and player pages use `useHostSession` and `usePlayerSession`, respectively.
Both expose the same live game state from one Pinia-owned session; the session
registers transport listeners once and recovers the active player or host on
reconnection. Shared snapshot, host, and player behavior live in
`src/stores/gameSession.ts`, `hostSession.ts`, and `playerSession.ts`.
Tests use the fake transport to exercise the same session behavior without a server.

## HTTP requests

The functions in `src/api/` use `requestJson` for status checks and JSON parsing.
It throws `HttpError` for unsuccessful HTTP responses, retaining the response for
resource-specific handling such as Pool refusals. Response types are generated
from the backend schema; they do not validate JSON at runtime.

Single-page request state uses `useAsyncState`. Its `run` captures failures in
`error`, which the caller must display; it retains the last successful `data`
on failure. If requests overlap, only the latest can update the state.

## Styling

The frontend uses Tailwind CSS 4 and daisyUI 5 via the Vite plugin. Add daisyUI
component classes and Tailwind utilities directly in Vue templates; use scoped
CSS only when an app-specific layout needs it. The built-in `light` and `dark`
themes follow the operating system's color preference. Theme configuration lives
in `src/style.css`.

The player's nine-column ticket scrolls horizontally on narrow screens. Keep
the scroll region keyboard-focusable and ticket topics readable when disabled.
