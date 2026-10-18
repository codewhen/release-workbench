import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "@xyflow/react/dist/style.css";
import "./style.css";
import { api } from "./shared/api";
import type { Catalog } from "./shared/types";
import { Home } from "./Home";
import { EditorLoader } from "./Editor";
import { navigate, useLocation } from "./navigation/location";
function App() {
  const [catalog, setCatalog] = useState<Catalog | null>(null),
    [error, setError] = useState("");
  const { workflow, run } = useLocation();
  useEffect(() => {
    api<Catalog>("catalog")
      .then(setCatalog)
      .catch((e) => setError(e.message));
  }, []);
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
      key={workflow + ":" + (run ?? "latest")}
      id={workflow}
      catalog={catalog}
      onHome={() =>
        navigate({
          workflow: null,
          view: undefined,
          graph: undefined,
          display: undefined,
          card: undefined,
          panel: undefined,
        })
      }
    />
  ) : (
    <Home
      catalog={catalog}
      onOpen={(id) =>
        navigate({
          workflow: id,
          view: undefined,
          graph: undefined,
          display: undefined,
          card: undefined,
          panel: undefined,
        })
      }
    />
  );
}
createRoot(document.getElementById("root")!).render(<App />);
