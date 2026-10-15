import { useCallback, useState } from "react";
import type { Workflow } from "../shared/types";
export function useEditor(initial: Workflow) {
  const [history, setHistory] = useState<Workflow[]>([initial]);
  const [index, setIndex] = useState(0);
  const commit = useCallback(
    (next: Workflow) => {
      setHistory((old) => [...old.slice(0, index + 1), next]);
      setIndex(index + 1);
    },
    [index],
  );
  const reset = useCallback((value: Workflow) => {
    setHistory([value]);
    setIndex(0);
  }, []);
  return {
    workflow: history[index],
    commit,
    reset,
    undo: () => setIndex((i) => Math.max(0, i - 1)),
    redo: () => setIndex((i) => Math.min(history.length - 1, i + 1)),
    canUndo: index > 0,
    canRedo: index < history.length - 1,
  };
}
