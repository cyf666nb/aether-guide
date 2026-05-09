import { ScanGlyph } from "@aether/design-system/icons";
import { TrustBar, VisitorNav } from "../components/VisitorChrome";

export default function PhotoPage() {
  return (
    <main className="tourist-frame photo-page">
      <img src="/scenes/lake.png" alt="湖泊取景背景" />
      <TrustBar mode="visual" />
      <VisitorNav />
      <div className="scan-beam" />
      <section className="viewfinder" aria-label="拍照识景取景框">
        <svg viewBox="0 0 320 320" role="img" aria-label="圆形取景框">
          <circle cx="160" cy="160" r="112" fill="none" stroke="currentColor" strokeWidth="1.25" />
          <path d="M80 56H52v42M240 56h28v42M80 264H52v-42M240 264h28v-42" fill="none" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" />
          <path d="M116 174c26 16 63 14 89-6" fill="none" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" />
        </svg>
      </section>
      <section className="result-sheet">
        <p className="caption">识别中 · VPS</p>
        <h1 className="type-heading type-heading-2">可能是月门听泉</h1>
        <p className="type-body">置信 87%。如果角度不对，可以换个角度试试，或者直接跟我聊聊附近的标识。</p>
        <ScanGlyph style={{ width: 42, color: "var(--gold-light)", marginTop: 16 }} />
      </section>
    </main>
  );
}

