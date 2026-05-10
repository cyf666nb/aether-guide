"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            retry: 1,
            // Most queries in this app hit seed/demo data that changes on
            // admin writes, not on every navigation. Favor fewer re-fetches.
            staleTime: 5 * 60_000,
            gcTime: 30 * 60_000,
            refetchOnWindowFocus: false,
            refetchOnReconnect: true
          }
        }
      })
  );

  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
