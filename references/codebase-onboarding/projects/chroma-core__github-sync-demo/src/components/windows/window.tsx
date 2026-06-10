"use client";

import React, { useRef, useEffect, useState, useCallback } from "react";
import {
  WindowState,
  useWindows,
  WindowCloseContext,
} from "@/contexts/window-context";
import { Button } from "@/components/ui/button";
import { X, Minus, Square, RotateCcw } from "lucide-react";

interface WindowProps {
  window: WindowState;
}

export function Window({ window }: WindowProps) {
  const {
    closeWindow,
    minimizeWindow,
    maximizeWindow,
    updateWindow,
    bringToFront,
  } = useWindows();
  const windowRef = useRef<HTMLDivElement>(null);
  const headerRef = useRef<HTMLDivElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const [resizeDirection, setResizeDirection] = useState<string>("");
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [windowStart, setWindowStart] = useState({
    x: 0,
    y: 0,
    width: 0,
    height: 0,
  });

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (
        e.target !== headerRef.current &&
        !headerRef.current?.contains(e.target as Node)
      ) {
        return;
      }

      bringToFront(window.id);
      setIsDragging(true);
      setDragStart({ x: e.clientX, y: e.clientY });
      setWindowStart({
        x: window.x,
        y: window.y,
        width: window.width,
        height: window.height,
      });
      e.preventDefault();
    },
    [window.id, window.x, window.y, window.width, window.height, bringToFront],
  );

  const handleResizeMouseDown = useCallback(
    (e: React.MouseEvent, direction: string) => {
      bringToFront(window.id);
      setIsResizing(true);
      setResizeDirection(direction);
      setDragStart({ x: e.clientX, y: e.clientY });
      setWindowStart({
        x: window.x,
        y: window.y,
        width: window.width,
        height: window.height,
      });
      e.preventDefault();
      e.stopPropagation();
    },
    [window.id, window.x, window.y, window.width, window.height, bringToFront],
  );

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isDragging) {
        const deltaX = e.clientX - dragStart.x;
        const deltaY = e.clientY - dragStart.y;

        updateWindow(window.id, {
          x: Math.max(0, windowStart.x + deltaX),
          y: Math.max(0, windowStart.y + deltaY),
        });
      } else if (isResizing) {
        const deltaX = e.clientX - dragStart.x;
        const deltaY = e.clientY - dragStart.y;

        let newX = windowStart.x;
        let newY = windowStart.y;
        let newWidth = windowStart.width;
        let newHeight = windowStart.height;

        if (resizeDirection.includes("n")) {
          newY = windowStart.y + deltaY;
          newHeight = windowStart.height - deltaY;
        }
        if (resizeDirection.includes("s")) {
          newHeight = windowStart.height + deltaY;
        }
        if (resizeDirection.includes("w")) {
          newX = windowStart.x + deltaX;
          newWidth = windowStart.width - deltaX;
        }
        if (resizeDirection.includes("e")) {
          newWidth = windowStart.width + deltaX;
        }

        newWidth = Math.max(200, newWidth);
        newHeight = Math.max(150, newHeight);

        if (newWidth === 200 && resizeDirection.includes("w")) {
          newX = windowStart.x + windowStart.width - 200;
        }
        if (newHeight === 150 && resizeDirection.includes("n")) {
          newY = windowStart.y + windowStart.height - 150;
        }

        updateWindow(window.id, {
          x: Math.max(0, newX),
          y: Math.max(0, newY),
          width: newWidth,
          height: newHeight,
        });
      }
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      setIsResizing(false);
      setResizeDirection("");
    };

    if (isDragging || isResizing) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
      return () => {
        document.removeEventListener("mousemove", handleMouseMove);
        document.removeEventListener("mouseup", handleMouseUp);
      };
    }
  }, [
    isDragging,
    isResizing,
    dragStart,
    windowStart,
    resizeDirection,
    window.id,
    updateWindow,
  ]);

  const handleWindowClick = useCallback(() => {
    bringToFront(window.id);
  }, [window.id, bringToFront]);

  if (window.isMinimized) {
    return null;
  }

  const commonStyles = {
    position: "fixed" as const,
    zIndex: window.zIndex,
    animation: "slideAndShadow 0.05s ease-out forwards",
    transform: "translate(6px, 6px)",
    boxShadow: "rgba(0, 0, 0, 0.1) 0px 0px 0px",
  };

  const windowStyle = window.isMaximized
    ? {
        ...commonStyles,
        top: 0,
        left: 0,
        width: "100vw",
        height: "100vh",
      }
    : {
        ...commonStyles,
        left: window.x,
        top: window.y,
        width: window.width,
        height: window.height,
      };

  return (
    <div
      ref={windowRef}
      className="bg-white border-[1.5px] border-black rounded-xs overflow-hidden select-none"
      style={windowStyle}
      onClick={handleWindowClick}
    >
      <style jsx>{`
        @keyframes slideAndShadow {
          to {
            transform: translate(0, 0);
            box-shadow: 6px 6px 0 rgba(0, 0, 0, 0.1);
          }
        }
      `}</style>
      <div
        ref={headerRef}
        className="bg-gray-50 px-3 py-1 flex items-center relative cursor-move"
        onMouseDown={handleMouseDown}
      >
        <div className="flex items-center gap-2 absolute left-3 cursor-default group">
          <button
            className="w-3 h-3 rounded-full bg-red-500 hover:bg-red-600 flex items-center justify-center"
            onClick={(e) => {
              e.stopPropagation();
              closeWindow(window.id);
            }}
          >
            <X className="h-2 w-2 text-red-800 opacity-0 group-hover:opacity-100 transition-opacity" />
          </button>
          <button
            className="w-3 h-3 rounded-full bg-yellow-500 hover:bg-yellow-600 flex items-center justify-center"
            onClick={(e) => {
              e.stopPropagation();
              minimizeWindow(window.id);
            }}
          >
            <Minus className="h-2 w-2 text-yellow-800 opacity-0 group-hover:opacity-100 transition-opacity" />
          </button>
          <button
            className="w-3 h-3 rounded-full bg-green-500 hover:bg-green-600 flex items-center justify-center"
            onClick={(e) => {
              e.stopPropagation();
              maximizeWindow(window.id);
            }}
          >
            {window.isMaximized ? (
              <RotateCcw className="h-2 w-2 text-green-800 opacity-0 group-hover:opacity-100 transition-opacity" />
            ) : (
              <Square className="h-2 w-2 text-green-800 opacity-0 group-hover:opacity-100 transition-opacity" />
            )}
          </button>
        </div>

        <div className="flex-1 text-center">
          <div className="text-xs font-medium text-gray-700 opacity-0 truncate mx-16">
            {window.title}
          </div>
        </div>
      </div>

      <div
        className="flex-1 overflow-auto"
        style={{ height: "calc(100% - 40px)" }}
      >
        <WindowCloseContext.Provider value={() => closeWindow(window.id)}>
          {window.content}
        </WindowCloseContext.Provider>
      </div>

      {!window.isMaximized && (
        <>
          <div
            className="absolute top-0 left-0 w-2 h-2 cursor-nw-resize"
            onMouseDown={(e) => handleResizeMouseDown(e, "nw")}
          />
          <div
            className="absolute top-0 right-0 w-2 h-2 cursor-ne-resize"
            onMouseDown={(e) => handleResizeMouseDown(e, "ne")}
          />
          <div
            className="absolute bottom-0 left-0 w-2 h-2 cursor-sw-resize"
            onMouseDown={(e) => handleResizeMouseDown(e, "sw")}
          />
          <div
            className="absolute bottom-0 right-0 w-2 h-2 cursor-se-resize"
            onMouseDown={(e) => handleResizeMouseDown(e, "se")}
          />

          <div
            className="absolute top-0 left-2 right-2 h-1 cursor-n-resize"
            onMouseDown={(e) => handleResizeMouseDown(e, "n")}
          />
          <div
            className="absolute bottom-0 left-2 right-2 h-1 cursor-s-resize"
            onMouseDown={(e) => handleResizeMouseDown(e, "s")}
          />
          <div
            className="absolute left-0 top-2 bottom-2 w-1 cursor-w-resize"
            onMouseDown={(e) => handleResizeMouseDown(e, "w")}
          />
          <div
            className="absolute right-0 top-2 bottom-2 w-1 cursor-e-resize"
            onMouseDown={(e) => handleResizeMouseDown(e, "e")}
          />
        </>
      )}
    </div>
  );
}
