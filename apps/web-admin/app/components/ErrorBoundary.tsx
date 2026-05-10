"use client";

import { Component, type ErrorInfo, type ReactNode } from "react";

type Props = {
  children: ReactNode;
  fallback?: (error: Error, reset: () => void) => ReactNode;
  onError?: (error: Error, info: ErrorInfo) => void;
};

type State = {
  error: Error | null;
};

/**
 * Top-level error boundary for the admin app.
 *
 * Mirrors `apps/web-tourist/app/components/ErrorBoundary.tsx`. We keep two
 * copies (instead of hoisting into design-system) because admin and tourist
 * have different visual languages — the fallback styling is not portable.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("[admin ErrorBoundary]", error, info.componentStack);
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
      style={{
        padding: "32px",
        margin: "48px auto",
        maxWidth: "640px",
        borderRadius: "12px",
        background: "#FFF8EC",
        border: "1px solid #E0C97F",
        color: "#3A2E1B",
        fontSize: "14px",
        lineHeight: 1.7,
      }}
    >
      <strong style={{ display: "block", marginBottom: "10px", fontSize: "18px" }}>
        管理台出现异常
      </strong>
      <p style={{ margin: "0 0 16px 0", fontFamily: "ui-monospace, monospace", fontSize: "12px" }}>
        {error.message || "未知错误。"}
      </p>
      <p style={{ margin: "0 0 16px 0", opacity: 0.75 }}>
        请尝试重新加载该模块；若反复出现，请把 trace id 复制给运维。
      </p>
      <button
        type="button"
        onClick={onReset}
        style={{
          padding: "8px 18px",
          borderRadius: "8px",
          border: "1px solid #B89B5E",
          background: "#FFF",
          color: "#3A2E1B",
          cursor: "pointer",
          fontSize: "13px",
        }}
      >
        重新加载
      </button>
    </div>
  );
}
