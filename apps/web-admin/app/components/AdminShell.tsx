"use client";

import { AetherLogo } from "@aether/design-system/icons";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { clearAdminToken, getAdminToken } from "../lib/api";

const links = [
  ["概览", "/"],
  ["知识库", "/knowledge"],
  ["Prompt", "/experiments"],
  ["形象", "/settings/atmosphere"],
  ["会话回放", "/replay"],
  ["告警", "/alerts"]
];

/**
 * Client-side auth gate. We render nothing until we've confirmed a token
 * exists in sessionStorage; this prevents the admin shell from flashing
 * for an unauthenticated visitor before the redirect lands.
 *
 * True server-side protection would require migrating the admin token to
 * an HttpOnly cookie so Next middleware can read it on the edge — out of
 * scope for this change.
 */
function useAdminGate(): "checking" | "authed" | "redirecting" {
  const router = useRouter();
  const [state, setState] = useState<"checking" | "authed" | "redirecting">(
    "checking",
  );
  useEffect(() => {
    if (typeof window !== "object") return;
    if (getAdminToken()) {
      setState("authed");
      return;
    }
    setState("redirecting");
    router.replace("/login");
  }, [router]);
  return state;
}

export function AdminShell({
  children,
  active = "/"
}: {
  children: React.ReactNode;
  active?: string;
}) {
  const gate = useAdminGate();
  if (gate !== "authed") {
    // Render an empty scaffold so layout height doesn't jump during redirect.
    return <main className="zhaji-shell admin-layout" aria-busy="true" />;
  }
  return (
    <main className="zhaji-shell admin-layout">
      <aside className="side-nav">
        <Link className="side-brand" href="/">
          <AetherLogo />
          <span>知行 · 札记</span>
        </Link>
        <nav className="side-links">
          {links.map(([label, href]) => (
            <Link
              className={active === href ? "active" : ""}
              href={href}
              key={`${label}-${href}`}
            >
              {label}
            </Link>
          ))}
          <button
            type="button"
            className="thin-button"
            style={{ marginTop: 16 }}
            onClick={() => {
              clearAdminToken();
              window.location.href = "/login";
            }}
          >
            退出登录
          </button>
        </nav>
      </aside>
      <section className="admin-main">{children}</section>
    </main>
  );
}

export function AdminHeader({ eyebrow, title }: { eyebrow: string; title: string }) {
  return (
    <div className="admin-topline">
      <div>
        <p className="caption">{eyebrow}</p>
        <h1 className="type-heading type-heading-1">{title}</h1>
      </div>
      <span className="live-pill">实时数据 · 2s ago</span>
    </div>
  );
}
