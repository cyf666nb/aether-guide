import { KnowledgeMark } from "@aether/design-system/icons";
import { AdminHeader, AdminShell } from "../components/AdminShell";

export default function KnowledgePage() {
  return (
    <AdminShell active="/knowledge">
      <AdminHeader eyebrow="Knowledge Base" title="文档版本与检索痕迹" />
      <section className="knowledge-grid">
        <aside className="doc-tree">
          <KnowledgeMark style={{ width: 40, color: "var(--accent-500)" }} />
          <h2 className="type-heading type-heading-3" style={{ marginTop: 16 }}>
            月门听泉资料包
          </h2>
          <div className="scan-document" style={{ marginTop: 20 }} />
          <p className="type-body" style={{ marginTop: 16 }}>
            上传扫描中，完成后进入 arq 索引队列。
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
          <h2 className="type-heading type-heading-2">月门借景与水声设计</h2>
          <p className="type-body" style={{ marginTop: 16 }}>
            月门面向东侧水面，清晨逆光时形成半透明轮廓。讲解时应先提示游客站在桥面左侧，
            再说明“借景”如何把远山压入门洞。
          </p>
          <div className="chunk">
            <p className="caption">Retrieved 38 times</p>
            <p className="type-body">chunk: moon-gate / section: garden-sound / score: 0.92</p>
          </div>
          <div className="chunk" style={{ borderLeftColor: "var(--ember)", background: "rgba(178, 58, 47, 0.08)" }}>
            <p className="caption">Diff removed</p>
            <p className="type-body">旧版“最佳拍照点在正午”已删除，避免错误推荐。</p>
          </div>
        </article>
      </section>
    </AdminShell>
  );
}

