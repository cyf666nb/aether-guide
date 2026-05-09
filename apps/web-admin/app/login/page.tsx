"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { adminLogin, getAdminToken } from "../lib/api";

const IS_DEV = process.env.NODE_ENV === "development";

export default function LoginPage() {
  const router = useRouter();
  // Only prefill demo credentials in development — never in production bundles.
  const [email, setEmail] = useState(IS_DEV ? "admin@demo" : "");
  const [password, setPassword] = useState(IS_DEV ? "admin-demo-pass" : "");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Redirect on mount if already authenticated — must be in an effect,
  // not render body (React forbids triggering navigation during render).
  useEffect(() => {
    if (typeof window === "object" && getAdminToken()) {
      router.replace("/");
    }
  }, [router]);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await adminLogin(email, password);
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "登录失败。");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ maxWidth: 420, margin: "12vh auto", padding: 32 }}>
      <h1 className="type-heading type-heading-2">札记 · 登录</h1>
      <p className="type-body" style={{ marginTop: 8 }}>
        使用管理员账号进入管理台。
      </p>
      <form onSubmit={submit} style={{ marginTop: 24, display: "grid", gap: 16 }}>
        <label style={{ display: "grid", gap: 6 }}>
          <span className="caption">邮箱</span>
          <input
            type="email"
            className="field-line"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            required
          />
        </label>
        <label style={{ display: "grid", gap: 6 }}>
          <span className="caption">密码</span>
          <input
            type="password"
            className="field-line"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </label>
        {error ? (
          <p className="type-body" role="alert" style={{ color: "var(--ember)" }}>
            {error}
          </p>
        ) : null}
        <button className="primary-button" type="submit" disabled={loading}>
          {loading ? "正在登录…" : "登录"}
        </button>
      </form>
    </main>
  );
}
