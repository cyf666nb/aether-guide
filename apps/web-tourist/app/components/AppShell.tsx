"use client";

import { TrustBar, VisitorNav } from "./VisitorChrome";
import { useNavState } from "./NavContext";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { trustMode, connectionState } = useNavState();
  return (
    <div className="app-shell">
      <TrustBar mode={trustMode} state={connectionState} />
      <VisitorNav />
      <div className="app-content">{children}</div>
    </div>
  );
}
