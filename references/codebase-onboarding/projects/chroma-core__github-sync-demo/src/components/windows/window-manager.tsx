"use client";

import React from "react";
import { useWindows } from "@/contexts/window-context";
import { Window } from "./window";

export function WindowManager() {
  const { windows } = useWindows();

  return (
    <div className="fixed inset-0 pointer-events-none z-50">
      {windows.map((window) => (
        <div key={window.id} className="pointer-events-auto">
          <Window window={window} />
        </div>
      ))}
    </div>
  );
}
