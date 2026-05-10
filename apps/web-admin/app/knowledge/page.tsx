import { KnowledgeMark } from "@aether/design-system/icons";
import { AdminHeader, AdminShell } from "../components/AdminShell";

export default function KnowledgePage() {
  return (
    <AdminShell active="/knowledge">
      <AdminHeader eyebrow="Knowledge Base" title="三坊七巷知识库与检索记录" />
      <section className="knowledge-grid">
        <aside className="doc-tree">
          <KnowledgeMark style={{ width: 40, color: "var(--accent-500)" }} />
          <h2 className="type-heading type-heading-3" style={{ marginTop: 16 }}>
            福州三坊七巷资料包
          </h2>
          <div className="scan-document" style={{ marginTop: 20 }} />
          <p className="type-body" style={{ marginTop: 16 }}>
            南后街、名人故居、古厝建筑与非遗演艺已进入本地 RAG 索引。
          </p>
        </aside>
        <aside className="version-rail">
          <p className="caption">Version</p>
          {["v3 live", "v2 canary", "v1 archived"].map((item) => (
            <p className="type-mono" style={{ marginTop: 18 }} key={item}>
              {item}
            </p>
          ))}
        </aside>
        <article className="doc-preview">
          <p className="caption">Preview</p>
          <h2 className="type-heading type-heading-2">南后街与名人故居动线</h2>
          <p className="type-body" style={{ marginTop: 16 }}>
            首次到访建议从南后街进入，先建立“三坊七巷是福州古城肌理”的整体印象，
            再转入林觉民·冰心故居、严复故居和小黄楼，形成文学、近代思想与古厝建筑的连续讲解。
          </p>
          <div className="chunk">
            <p className="caption">Retrieved 38 times</p>
            <p className="type-body">
              chunk: nanhou-street / section: route-intro / score: 0.92
            </p>
          </div>
          <div
            className="chunk"
            style={{ borderLeftColor: "var(--ember)", background: "rgba(178, 58, 47, 0.08)" }}
          >
            <p className="caption">Diff removed</p>
            <p className="type-body">
              已移除“只推荐夜游”的旧描述，避免忽略故居开放时间与白天研学路线。
            </p>
          </div>
        </article>
      </section>
    </AdminShell>
  );
}
