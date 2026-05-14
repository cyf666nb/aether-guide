"use client";

import { createContext, useCallback, useContext, useState } from "react";

type TrustMode = "online" | "visual" | "offline";
type ConnectionState = "connecting" | "online" | "offline" | "reconnecting";

interface NavContextValue {
  trustMode: TrustMode;
  connectionState: ConnectionState | undefined;
  setNav: (mode: TrustMode, state?: ConnectionState) => void;
}

const NavContext = createContext<NavContextValue>({
  trustMode: "online",
  connectionState: undefined,
  setNav: () => {},
});

export function NavProvider({ children }: { children: React.ReactNode }) {
  const [trustMode, setTrustMode] = useState<TrustMode>("online");
  const [connectionState, setConnectionState] = useState<
    ConnectionState | undefined
  >(undefined);

  const setNav = useCallback(
    (mode: TrustMode, state?: ConnectionState) => {
      setTrustMode(mode);
      setConnectionState(state);
    },
    [],
  );

  return (
    <NavContext.Provider value={{ trustMode, connectionState, setNav }}>
      {children}
    </NavContext.Provider>
  );
}

export function useNavState() {
  return useContext(NavContext);
}
