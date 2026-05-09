"use client";

import { atmospheres } from "@aether/design-system/demo-data";
import { useQuery } from "@tanstack/react-query";
import { TrustBar, VisitorNav } from "../components/VisitorChrome";
import { getRoute } from "../lib/api";

const times = ["09:30", "10:10", "11:05"];

export default function RoutePage() {
  const { data: route } = useQuery({
    queryKey: ["route"],
    queryFn: () => getRoute()
  });
  const sceneCycle = atmospheres.slice(0, 3);

  return (
    <main className="tourist-frame route-page">
      <TrustBar />
      <VisitorNav />
      <section className="route-intro">
        <p className="caption">Route Design</p>
        <h1 className="type-heading type-heading-1">
          今天 3 小时 · 偏爱水景与高处视野 · 避开正午直晒
        </h1>
        <p className="type-body">我给你设计了这条路，全程约 {route?.total_walk_minutes ?? 16} 分钟步行。</p>
      </section>
      <section className="timeline">
        {(route?.stops ?? []).map((stop, index) => (
          <article className="route-card" key={stop.landmark_id}>
            <div className="time-stamp">{times[index] ?? "11:40"}</div>
            <div className="route-photo photo-zoom">
              <img src={sceneCycle[index]?.scene ?? "/scenes/forest.png"} alt={stop.name} />
              <div className="route-copy">
                <p className="caption">{index === 0 ? "Start" : `步行 ${stop.walk_minutes_from_previous} 分钟`}</p>
                <h2 className="type-heading type-heading-2">{stop.name}</h2>
                <p className="type-body">{stop.reason}</p>
              </div>
            </div>
            {index < (route?.stops.length ?? 0) - 1 && (
              <>
                <div />
                <p className="walk-line">步行 {route?.stops[index + 1]?.walk_minutes_from_previous ?? 8} 分钟</p>
              </>
            )}
          </article>
        ))}
      </section>
      <button className="primary-button" style={{ position: "sticky", bottom: 18, width: "100%", marginTop: 24 }} type="button">
        开始游览
      </button>
    </main>
  );
}

