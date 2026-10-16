/** One cancellable state poll at a time; stale polls cannot overwrite a newly started run. */
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../shared/api";
import { EMPTY_STATE, type RunState } from "../shared/types";
export function useRunState(id: string, onError: (message: string) => void) {
  const [state, replace] = useState<RunState>(EMPTY_STATE);
  const generation = useRef(0);
  const setState = useCallback((value: RunState) => {
    generation.current += 1;
    replace(value);
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;
    const poll = async () => {
      const requested = generation.current;
      try {
        const value = await api<RunState>(
          "state",
          undefined,
          id,
          controller.signal,
        );
        if (!controller.signal.aborted && requested === generation.current)
          replace(value);
      } catch (error) {
        if (!controller.signal.aborted && requested === generation.current)
          onError(error instanceof Error ? error.message : String(error));
      } finally {
        if (!controller.signal.aborted)
          timer = setTimeout(() => void poll(), 500);
      }
    };
    void poll();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [id, onError]);
  return { state, setState };
}
