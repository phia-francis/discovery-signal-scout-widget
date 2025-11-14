import React from "react";
import ReactDOM from "react-dom/client";
import SignalScoutWidget from "./SignalScoutWidget";

const DEFAULT_JSON = `${location.origin}${location.pathname.replace(/\/$/, "")}`
  .replace(/\/widget\/?$/, "") + "/signals/latest.json";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <SignalScoutWidget
      title="Signal Scout"
      initialUrl={DEFAULT_JSON}
      autoRefreshMs={300000}
    />
  </React.StrictMode>
);
