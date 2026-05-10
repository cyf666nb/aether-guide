"use client";

import Image from "next/image";
import { atmospheres, type Atmosphere } from "@aether/design-system/demo-data";
import { useEffect, useState } from "react";
import { AdminHeader, AdminShell } from "../../components/AdminShell";

const STORAGE_KEY = "aether-atmosphere";

function applyAtmosphere(id: Atmosphere) {
  document.documentElement.classList.remove(
    "atmosphere-lake",
    "atmosphere-dusk",
    "atmosphere-ocean",
    "atmosphere-desert"
  );
  if (id !== "forest") {
    document.documentElement.classList.add(`atmosphere-${id}`);
  }
}

export default function AtmospherePage() {
  const [selected, setSelected] = useState<Atmosphere>("forest");

  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY) as Atmosphere | null;
    if (saved && atmospheres.some((a) => a.id === saved)) {
      setSelected(saved);
      applyAtmosphere(saved);
    }
  }, []);

  useEffect(() => {
    applyAtmosphere(selected);
    localStorage.setItem(STORAGE_KEY, selected);
  }, [selected]);

  return (
    <AdminShell active="/settings/atmosphere">
      <AdminHeader eyebrow="Atmosphere" title="多租户氛围切换" />
      <section className="atmosphere-grid">
        {atmospheres.map((item) => (
          <button
            className="atmosphere-card"
            key={item.id}
            onClick={() => setSelected(item.id)}
            style={{ textAlign: "left", padding: 0, color: "var(--text-primary)" }}
            type="button"
          >
            <div style={{ position: "relative", width: "100%", aspectRatio: "16 / 10" }}>
              <Image
                src={item.scene}
                alt={item.name}
                fill
                sizes="(max-width: 768px) 100vw, 360px"
                style={{ objectFit: "cover" }}
              />
            </div>
            <div>
              <span className="swatch" style={{ background: item.accent }} />
              <h2 className="type-heading type-heading-3" style={{ marginTop: 12 }}>
                {item.name}
              </h2>
              <p className="type-body">{item.bestFor}</p>
            </div>
          </button>
        ))}
      </section>
      <section className="metric-tile" style={{ marginTop: 18 }}>
        <p className="caption">Live Preview</p>
        <p className="big-number" style={{ fontSize: 76 }}>
          {selected}
        </p>
        <p className="type-body">切换时只改变 CSS 变量，页面布局保持稳定。</p>
      </section>
    </AdminShell>
  );
}

