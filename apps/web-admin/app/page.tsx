"use client";

import { dashboardMetrics } from "@aether/design-system/demo-data";
import { useQuery } from "@tanstack/react-query";
import { AdminHeader, AdminShell } from "./components/AdminShell";
import { TrafficLine } from "./components/Charts";
import { getDashboard, getLandmarks } from "./lib/api";

export default function DashboardPage() {
  const { data: dashboard } = useQuery({ queryKey: ["dashboard"], queryFn: getDashboard });
  const { data: landmarks = [] } = useQuery({ queryKey: ["admin-landmarks"], queryFn: getLandmarks });

  return (
    <AdminShell active="/">
      <AdminHeader eyebrow="Overview" title="景区实时运营头版" />
      <section className="dashboard-grid">
        <article className="metric-tile span-5">
          <p className="caption">服务游客</p>
          <p className="big-number">{dashboard?.active_sessions != null ? dashboard.active_sessions.toLocaleString() : dashboardMetrics.visitors}</p>
          <p className="trend">↑ 12% 昨日</p>
        </article>
        <article className="metric-tile span-4">
          <p className="caption">平均满意度</p>
          <p className="big-number">{dashboard?.nps != null ? dashboard.nps.toFixed(1) : dashboardMetrics.satisfaction}</p>
          <p className="trend">↑ 0.2 / 5</p>
        </article>
        <article className="metric-tile span-3">
          <p className="caption">首音 P95</p>
          <p className="big-number" style={{ fontSize: 58 }}>
            {dashboardMetrics.p95}
          </p>
          <p className="trend">SLO 内</p>
        </article>
        <article className="work-tile span-7">
          <div style={{ padding: "20px 24px 0" }}>
            <p className="caption">24h 流量曲线</p>
            <h2 className="type-heading type-heading-3">午后高峰由路线推荐分流</h2>
          </div>
          <TrafficLine />
        </article>
        <article className="work-tile span-5">
          <div className="rank-list">
            <p className="caption">热点景点</p>
            {landmarks.map((landmark, index) => (
              <div className="rank-item" key={landmark.id}>
                <span className="type-mono">{String(index + 1).padStart(2, "0")}</span>
                <span>{landmark.name}</span>
                <span className="trend">+{18 - index * 4}%</span>
              </div>
            ))}
          </div>
        </article>
        <article className="metric-tile span-4">
          <p className="caption">Token 成本</p>
          <p className="big-number" style={{ fontSize: 72 }}>
            ${dashboard?.token_cost_usd_today != null ? dashboard.token_cost_usd_today.toFixed(1) : "12.4"}
          </p>
          <p className="type-body">今日服务成本，对比真人导游约 ¥800。</p>
        </article>
        <article className="metric-tile span-4">
          <p className="caption">语义缓存</p>
          <p className="big-number" style={{ fontSize: 72 }}>
            {dashboard?.cache_hit_rate != null ? Math.round(dashboard.cache_hit_rate * 100) : 78}%
          </p>
          <p className="trend">二次相似问题首响更快</p>
        </article>
      </section>
    </AdminShell>
  );
}

