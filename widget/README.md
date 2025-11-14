# Signal Scout Widget

React widget for browsing Signal Scout outputs. The component expects to load
`signals/latest.json` produced by the agent workflow.

## Usage

```tsx
import SignalScoutWidget from "./SignalScoutWidget";

const DEFAULT_JSON = `${location.origin}${location.pathname.replace(/\/$/, "")}`
  .replace(/\/widget\/?$/, "") + "/signals/latest.json";

export default function App() {
  return (
    <SignalScoutWidget
      title="Signal Scout"
      initialUrl={DEFAULT_JSON}
      initialUrl="/signals/latest.json"
      autoRefreshMs={300_000}
    />
  );
}
```

### Key features

- Mission-Radar summaries rendered with safe markdown (🔎/💡/📡 blocks).
- Mission, archetype, focus, brand, date, score and text search filters.
- Mission and category keyword chips driven by the Excel-enhanced agent.
- CSV/JSON export, manual JSON upload and optional periodic refresh.
- Default deployment expects GitHub Pages with agent JSON published under `/signals/`.

### Working behind a proxy

If your network blocks direct access to the public npm registry, create three
repository or environment secrets for the workflows:

- `NPM_REGISTRY_URL` – alternative registry root (defaults to `https://registry.npmjs.org`).
- `NPM_HTTP_PROXY` / `NPM_HTTPS_PROXY` – proxy endpoints for HTTP/HTTPS traffic.

The `deploy-widget` workflow reads these secrets and configures `npm` before
installing packages. For local development you can run the same commands
manually:

```bash
cd widget
npm config set registry "${NPM_REGISTRY_URL:-https://registry.npmjs.org}"
[ -n "${NPM_HTTP_PROXY}" ] && npm config set proxy "$NPM_HTTP_PROXY"
[ -n "${NPM_HTTPS_PROXY}" ] && npm config set https-proxy "$NPM_HTTPS_PROXY"
npm install
```

Once the proxy configuration is in place, Vite builds (`npm run build`) will
work without attempting to bypass your corporate gateway.
Placeholder directory for the React-based Signal Scout widget. The widget will consume
`signals/latest.json` produced by the agent workflow when implemented.
