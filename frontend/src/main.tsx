import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "@xyflow/react/dist/style.css";
import "./style.css";
import { api } from "./shared/api";
import type { Catalog } from "./shared/types";
import { Home } from "./Home";
import { EditorLoader } from "./Editor";
function App() {
  const [catalog, setCatalog] = useState<Catalog | null>(null),
    [error, setError] = useState(""),
    [workflow, setWorkflow] = useState(
      new URLSearchParams(location.search).get("workflow"),
    );
  useEffect(() => {
    api<Catalog>("catalog")
      .then(setCatalog)
      .catch((e) => setError(e.message));
  }, []);
  function navigate(id: string | null) {
    history.replaceState(
      null,
      "",
      id ? "?workflow=" + encodeURIComponent(id) : location.pathname,
    );
    setWorkflow(id);
  }
  if (!catalog)
    return (
      <main className="loading">
        <h1>Workflow Workbench</h1>
        <p role={error ? "alert" : "status"}>
          {error || "Loading the card catalog…"}
        </p>
      </main>
    );
  return workflow ? (
    <EditorLoader
      key={workflow}
      id={workflow}
      catalog={catalog}
      onHome={() => navigate(null)}
    />
  ) : (
    <Home catalog={catalog} onOpen={(id) => navigate(id)} />
  );
}
createRoot(document.getElementById("root")!).render(<App />);
