import Link from "next/link";
import { AetherLogo } from "@aether/design-system/icons";
import { ThemeToggle } from "@aether/design-system";

type TrustMode = "online" | "visual" | "offline";
type ConnectionState = "connecting" | "online" | "offline" | "reconnecting";

const MODE_COPY: Record<TrustMode, string> = {
  online: "实时 · 在线导览",
  visual: "视觉定位 · 现场识景",
  offline: "离线模式 · 本地知识库",
};

const STATE_COPY: Partial<Record<ConnectionState, string>> = {
  connecting: "正在连接…",
  reconnecting: "连接已断开 · 正在重连",
  offline: "无网络",
};

export function TrustBar({
  mode = "online",
  state,
}: {
  mode?: TrustMode;
  state?: ConnectionState;
}) {
  const primary = MODE_COPY[mode];
  const secondary = state ? STATE_COPY[state] : undefined;
  return (
    <div className="trust-bar" role="status" aria-live="polite">
      {primary}
      {secondary ? ` · ${secondary}` : null}
    </div>
  );
}

export function VisitorNav() {
  return (
    <nav className="visitor-nav">
      <Link className="nav-brand" href="/">
        <AetherLogo />
        <span>知行 · 临境</span>
      </Link>
      <div className="nav-links">
        <Link className="thin-button" href="/landmarks">
          景点
        </Link>
        <Link className="thin-button" href="/route">
          路线
        </Link>
        <Link className="thin-button" href="/photo">
          拍照
        </Link>
      </div>
      <ThemeToggle />
    </nav>
  );
}
