import Link from "next/link";
import { AetherLogo } from "@aether/design-system/icons";

const links = [
  ["概览", "/"],
  ["知识库", "/knowledge"],
  ["Prompt", "/experiments"],
  ["形象", "/settings/atmosphere"],
  ["会话回放", "/replay"],
  ["告警", "/alerts"]
];

export function AdminShell({ children, active = "/" }: { children: React.ReactNode; active?: string }) {
  return (
    <main className="zhaji-shell admin-layout">
      <aside className="side-nav">
        <Link className="side-brand" href="/">
          <AetherLogo />
          <span>知行 · 札记</span>
        </Link>
        <nav className="side-links">
          {links.map(([label, href]) => (
            <Link className={active === href ? "active" : ""} href={href} key={`${label}-${href}`}>
              {label}
            </Link>
          ))}
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

