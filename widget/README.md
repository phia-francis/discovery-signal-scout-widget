# Signal Scout Widget

React widget for browsing Signal Scout outputs. The component expects to load
`signals/latest.json` produced by the agent workflow.

## Usage

```tsx
import SignalScoutWidget from "./SignalScoutWidget";

export default function App() {
  return (
    <SignalScoutWidget
      title="Signal Scout"
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
