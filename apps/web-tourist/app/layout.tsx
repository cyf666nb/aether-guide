import type { Metadata, Viewport } from "next";
import "./globals.css";
import "./linjing.css";
import { AtmosphereInit, Providers } from "@aether/design-system";

export const metadata: Metadata = {
  title: "临境 · 知行导览",
  description: "Immersive tourist-side scenic digital human guide."
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#0B0E10"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" data-theme="linjing" className="atmosphere-forest">
      <body>
        <AtmosphereInit />
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
