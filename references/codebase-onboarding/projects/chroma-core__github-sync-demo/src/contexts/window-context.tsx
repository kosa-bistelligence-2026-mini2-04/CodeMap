"use client";

import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  ReactNode,
} from "react";

export interface WindowState {
  id: string;
  title: string;
  content: ReactNode;
  x: number;
  y: number;
  width: number;
  height: number;
  zIndex: number;
  isMinimized: boolean;
  isMaximized: boolean;
}

type OpenWindowParams = Omit<WindowState, "id" | "zIndex" | "x" | "y"> & {
  x?: number;
  y?: number;
};

interface WindowContextType {
  windows: WindowState[];
  openWindow: (window: OpenWindowParams) => string;
  closeWindow: (id: string) => void;
  minimizeWindow: (id: string) => void;
  maximizeWindow: (id: string) => void;
  updateWindow: (id: string, updates: Partial<WindowState>) => void;
  bringToFront: (id: string) => void;
}

const WindowContext = createContext<WindowContextType | undefined>(undefined);

export const WindowCloseContext = createContext<(() => void) | null>(null);

export function useWindowClose() {
  return useContext(WindowCloseContext);
}

export function useWindows() {
  const context = useContext(WindowContext);
  if (!context) {
    throw new Error("useWindows must be used within a WindowProvider");
  }
  return context;
}

interface WindowProviderProps {
  children: ReactNode;
}

export function WindowProvider({ children }: WindowProviderProps) {
  const [windows, setWindows] = useState<WindowState[]>([]);
  const [nextZIndex, setNextZIndex] = useState(1000);

  const getCenteredPosition = useCallback(
    (width: number, height: number) => {
      const screenWidth =
        typeof window !== "undefined" ? window.innerWidth : 1200;
      const screenHeight =
        typeof window !== "undefined" ? window.innerHeight : 800;

      const baseX = Math.max(0, (screenWidth - width) / 2);
      const baseY = Math.max(0, (screenHeight - height) / 2);

      const radius = 30;
      const steps = 8;
      const angle = (windows.length % steps) * ((2 * Math.PI) / steps);

      return {
        x: baseX + Math.cos(angle) * radius,
        y: baseY + Math.sin(angle) * radius,
      };
    },
    [windows.length],
  );

  const openWindow = useCallback(
    (windowData: OpenWindowParams) => {
      const id = `window-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

      const screenWidth =
        typeof window !== "undefined" ? window.innerWidth : 1200;
      const isMobile = screenWidth < 768;

      const position =
        windowData.x !== undefined && windowData.y !== undefined
          ? { x: windowData.x, y: windowData.y }
          : getCenteredPosition(windowData.width, windowData.height);

      const newWindow: WindowState = {
        ...windowData,
        ...position,
        id,
        zIndex: nextZIndex,
        isMaximized: isMobile ? true : windowData.isMaximized,
      };

      setWindows((prev) => [...prev, newWindow]);
      setNextZIndex((prev) => prev + 1);
      return id;
    },
    [nextZIndex, getCenteredPosition],
  );

  const closeWindow = useCallback((id: string) => {
    setWindows((prev) => prev.filter((window) => window.id !== id));
  }, []);

  const minimizeWindow = useCallback((id: string) => {
    setWindows((prev) =>
      prev.map((window) =>
        window.id === id
          ? { ...window, isMinimized: !window.isMinimized }
          : window,
      ),
    );
  }, []);

  const maximizeWindow = useCallback((id: string) => {
    setWindows((prev) =>
      prev.map((window) =>
        window.id === id
          ? { ...window, isMaximized: !window.isMaximized }
          : window,
      ),
    );
  }, []);

  const updateWindow = useCallback(
    (id: string, updates: Partial<WindowState>) => {
      setWindows((prev) =>
        prev.map((window) =>
          window.id === id ? { ...window, ...updates } : window,
        ),
      );
    },
    [],
  );

  const bringToFront = useCallback(
    (id: string) => {
      setWindows((prev) =>
        prev.map((window) =>
          window.id === id ? { ...window, zIndex: nextZIndex } : window,
        ),
      );
      setNextZIndex((prev) => prev + 1);
    },
    [nextZIndex],
  );

  const value: WindowContextType = {
    windows,
    openWindow,
    closeWindow,
    minimizeWindow,
    maximizeWindow,
    updateWindow,
    bringToFront,
  };

  return (
    <WindowContext.Provider value={value}>{children}</WindowContext.Provider>
  );
}
