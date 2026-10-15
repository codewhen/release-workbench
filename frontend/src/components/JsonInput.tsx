import { useEffect, useState, useRef, useId } from "react";
export function JsonInput({
  label,
  value,
  onChange,
  disabled = false,
  multiline = false,
  onInvalid,
}: {
  label: string;
  value: unknown;
  onChange: (value: unknown) => void;
  disabled?: boolean;
  multiline?: boolean;
  onInvalid?: (error: string) => void;
}) {
  const element = useRef<HTMLInputElement | HTMLTextAreaElement | null>(null),
    errorId = useId();
  const serialized = JSON.stringify(
    value ?? null,
    multiline ? null : undefined,
    multiline ? 2 : undefined,
  );
  const [text, setText] = useState(serialized),
    [error, setError] = useState("");
  useEffect(() => {
    setText(serialized);
    setError("");
    element.current?.setCustomValidity("");
    onInvalid?.("");
  }, [serialized]);
  const update = (next: string) => {
    setText(next);
    try {
      const parsed: unknown = JSON.parse(next);
      setError("");
      element.current?.setCustomValidity("");
      onInvalid?.("");
      onChange(parsed);
    } catch {
      setError("Enter valid JSON, including quotes around text.");
      element.current?.setCustomValidity(
        "Enter valid JSON, including quotes around text.",
      );
      onInvalid?.("Invalid JSON in " + label);
    }
  };
  return (
    <label className="json-field">
      {label}
      {multiline ? (
        <textarea
          className="nodrag code"
          aria-label={label}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? errorId : undefined}
          ref={(node) => {
            element.current = node;
          }}
          disabled={disabled}
          value={text}
          onChange={(e) => update(e.target.value)}
        />
      ) : (
        <input
          className="nodrag code"
          aria-label={label}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? errorId : undefined}
          ref={(node) => {
            element.current = node;
          }}
          disabled={disabled}
          value={text}
          onChange={(e) => update(e.target.value)}
        />
      )}{" "}
      {error && (
        <small role="alert" id={errorId} className="error">
          {error}
        </small>
      )}
    </label>
  );
}
