"use client";

import { useQuery } from "@tanstack/react-query";
import { AdminHeader, AdminShell } from "../components/AdminShell";
import { EventTrack, WaveTrack } from "../components/Charts";
import { getReplay } from "../lib/api";

export default function ReplayPage() {
  const { data } = useQuery({ queryKey: ["replay"], queryFn: () => getReplay() });
  return (
    <AdminShell active="/replay">
      <AdminHeader eyebrow="Session Replay" title="三层时间轴回放" />
      <section className="replay-panel" style={{ padding: 24 }}>
        <p className="caption">用户语音波形</p>
        <div className="replay-tracks">
          <WaveTrack />
          <WaveTrack variant="tts" />
          <EventTrack />
        </div>
        <div className="replay-detail">
          <article className="panel-line" style={{ padding: 18 }}>
            <p className="caption">同步文本</p>
            <h2 className="type-heading type-heading-3">这座桥为什么叫墨桥？</h2>
            <p className="type-body" style={{ marginTop: 12 }}>
              系统在 420ms 内检索到 3 个 chunk，并在 2.6s 触发 TTS 首音。
            </p>
          </article>
          <article className="panel-line" style={{ padding: 18 }}>
            <p className="caption">检索 chunk</p>
            {(data?.retrieved_chunks ?? []).map((chunk) => (
              <p className="type-mono" style={{ marginTop: 10 }} key={chunk}>
                {chunk}
              </p>
            ))}
            <button className="primary-button" style={{ marginTop: 18 }} type="button">
              这答错了 · 回流评测集
            </button>
          </article>
        </div>
      </section>
    </AdminShell>
  );
}

