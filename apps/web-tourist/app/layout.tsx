import type { Metadata, Viewport } from "next";
import Script from "next/script";
import "./globals.css";
import "./linjing.css";
import { AtmosphereInit, Providers } from "@aether/design-system";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { NavProvider } from "./components/NavContext";
import { AppShell } from "./components/AppShell";

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
        {/*
          Live2D Cubism 5 Core — must be loaded before any Live2DModel.from()
          call. `beforeInteractive` injects the script into <head> so that
          window.Live2DCubismCore is defined by the time our client
          components hydrate.
        */}
        <Script
          src="/live2d/live2dcubismcore.min.js"
          strategy="beforeInteractive"
        />
        <AtmosphereInit />
        <Providers>
          <ErrorBoundary>
            <NavProvider>
              <AppShell>{children}</AppShell>
            </NavProvider>
          </ErrorBoundary>
        </Providers>
      </body>
    </html>
  );
}
