import Link from "next/link";
import { AetherLogo } from "@aether/design-system/icons";

export function TrustBar({ mode = "online" }: { mode?: "online" | "visual" | "offline" }) {
  const copy = {
    online: "GPS 定位 · 精度 8m  |  在线  |  流畅",
    visual: "视觉定位 · 置信 87%  |  弱网  |  节能",
    offline: "离线模式 · 本地知识库  |  无网  |  节能"
  };
  return <div className="trust-bar">{copy[mode]}</div>;
}

export function VisitorNav() {
  return (
    <nav className="visitor-nav">
      <Link className="nav-brand" href="/">
        <AetherLogo />
        <span>知行 · 临境</span>
      </Link>
      <div className="nav-links">
        <Link className="thin-button" href="/photo">
          景点
        </Link>
        <Link className="thin-button" href="/route">
          路线
        </Link>
      </div>
    </nav>
  );
}

