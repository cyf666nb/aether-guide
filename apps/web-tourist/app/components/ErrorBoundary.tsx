"use client";

import { Component, type ErrorInfo, type ReactNode } from "react";

type Props = {
  children: ReactNode;
  /** Optional fallback. Receives the caught error and a reset callback. */
  fallback?: (error: Error, reset: () => void) => ReactNode;
  /** Called once when an error is caught. Use for logging / telemetry. */
  onError?: (error: Error, info: ErrorInfo) => void;
};

type State = {
  error: Error | null;
};

/**
 * Top-level error boundary for the tourist app.
 *
 * React 19 still requires a class component for componentDidCatch — there is
 * no hooks-based equivalent. This component is intentionally tiny: it only
 * catches *render* errors. Network/async errors should be handled by
 * TanStack Query (`onError` / error UI) closer to the call site.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // Surface to console even when no onError is wired so dev mode is loud.
    console.error("[ErrorBoundary]", error, info.componentStack);
    this.props.onError?.(error, info);
  }

  private reset = (): void => {
    this.setState({ error: null });
  };

  render(): ReactNode {
    const { error } = this.state;
    if (error) {
      if (this.props.fallback) {
        return this.props.fallback(error, this.reset);
      }
      return <DefaultErrorFallback error={error} onReset={this.reset} />;
    }
    return this.props.children;
  }
}

function DefaultErrorFallback({
  error,
  onReset,
}: {
  error: Error;
  onReset: () => void;
}) {
  return (
    <div
      role="alert"
      className="error-fallback"
      style={{
        padding: "24px",
        margin: "16px auto",
        maxWidth: "560px",
        borderRadius: "16px",
        background: "rgba(196, 146, 74, 0.08)",
        border: "1px solid rgba(196, 146, 74, 0.25)",
        color: "#E8E4DC",
        fontSize: "14px",
        lineHeight: 1.6,
      }}
    >
      <strong style={{ display: "block", marginBottom: "8px", fontSize: "16px" }}>
        界面遇到一点小麻烦
      </strong>
      <p style={{ margin: "0 0 12px 0", opacity: 0.85 }}>
        {error.message || "未知错误。你可以点下方按钮重试，或刷新页面。"}
      </p>
      <button
        type="button"
        onClick={onReset}
        style={{
          padding: "8px 16px",
          borderRadius: "999px",
          border: "1px solid rgba(196, 146, 74, 0.5)",
          background: "transparent",
          color: "#E8E4DC",
          cursor: "pointer",
          fontSize: "13px",
        }}
      >
        重新加载
      </button>
    </div>
  );
}
