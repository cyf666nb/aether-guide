import type { Metadata, Viewport } from "next";
import "./globals.css";
import "./zhaji.css";
import { AtmosphereInit } from "./components/AtmosphereInit";
import { Providers } from "@aether/design-system";

export const metadata: Metadata = {
  title: "札记 · 知行管理台",
  description: "Modern scenic-area operations workbench for Aether Guide."
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#F6F3EC"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" data-theme="zhaji" className="atmosphere-forest">
      <body>
        <AtmosphereInit />
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
