import { ThinkingGlyph } from "@aether/design-system/icons";
import { AdminHeader, AdminShell } from "../components/AdminShell";

export default function ExperimentsPage() {
  return (
    <AdminShell active="/experiments">
      <AdminHeader eyebrow="Prompt Lab" title="A/B Prompt 实验台" />
      <section className="experiment-panel" style={{ padding: 24, marginBottom: 16 }}>
        <p className="caption">胜率温度计</p>
        <div className="thermometer" style={{ marginTop: 12 }}>
          <span />
        </div>
        <p className="type-body" style={{ marginTop: 10 }}>
          A 占 64% / B 占 36%，样本量 428，显著性接近阈值。
        </p>
      </section>
      <section className="experiment-grid">
        <article className="experiment-panel" style={{ padding: 18 }}>
          <p className="caption">Variant A</p>
          <pre className="editor-mock">{`system:
你是景区数字人导览员。
回答要短，必须引用来源。

style:
像高端纪录片旁白。`}</pre>
        </article>
        <article className="experiment-panel" style={{ padding: 18 }}>
          <p className="caption">Variant B</p>
          <pre className="editor-mock">{`system:
你是本景区的现场向导。
优先给路线建议和安全提醒。

style:
像国家公园档案员。`}</pre>
        </article>
      </section>
      <section className="experiment-panel" style={{ padding: 20, marginTop: 16 }}>
        <ThinkingGlyph style={{ width: 36, color: "var(--gold)" }} />
        <p className="type-body" style={{ marginTop: 10 }}>
          每回合记录 winner、用户反馈和关键词，标注后回流 RAG eval。
        </p>
      </section>
    </AdminShell>
  );
}

