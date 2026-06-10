"use client";

import React, { useState, useCallback, useEffect, useRef } from "react";
import { useWindowClose } from "@/contexts/window-context";

type Mode = "normal" | "insert" | "command";
type View = "vim" | "shell";

interface VimWindowProps {
  initialBuffer: string;
}

const SHELL_HELP = `Available commands:
  help      Show this help message
  nvim      Open neovim editor
  chroma    Try it out!
  exit      Close the window
`;

export function VimWindow({ initialBuffer }: VimWindowProps) {
  const onClose = useWindowClose();
  const [view, setView] = useState<View>("vim");
  const [buffer, setBuffer] = useState<string[]>(() =>
    initialBuffer.split("\n"),
  );
  const [cursor, setCursor] = useState({ line: 0, col: 0 });
  const [mode, setMode] = useState<Mode>("normal");
  const [pendingKey, setPendingKey] = useState<string | null>(null);
  const [commandInput, setCommandInput] = useState("");
  const [shellInput, setShellInput] = useState("");
  const [shellHistory, setShellHistory] = useState<string[]>([]);
  const containerRef = useRef<HTMLDivElement>(null);
  const lineRefs = useRef<Map<number, HTMLDivElement>>(new Map());
  const shellEndRef = useRef<HTMLDivElement>(null);

  const clampCursor = useCallback(
    (line: number, col: number, lines: string[]) => {
      const clampedLine = Math.max(0, Math.min(line, lines.length - 1));
      const lineLength = lines[clampedLine]?.length || 0;
      const maxCol =
        mode === "insert" ? lineLength : Math.max(0, lineLength - 1);
      const clampedCol = Math.max(0, Math.min(col, maxCol));
      return { line: clampedLine, col: clampedCol };
    },
    [mode],
  );

  useEffect(() => {
    if (view === "vim") {
      const lineEl = lineRefs.current.get(cursor.line);
      if (lineEl) {
        lineEl.scrollIntoView({ block: "nearest", behavior: "smooth" });
      }
    }
  }, [cursor.line, view]);

  useEffect(() => {
    if (view === "shell") {
      shellEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [shellHistory, view]);

  const findNextWordStart = useCallback(
    (line: number, col: number) => {
      const currentLine = buffer[line] || "";
      let c = col;
      let l = line;

      while (c < currentLine.length && !/\s/.test(currentLine[c])) c++;
      while (c < currentLine.length && /\s/.test(currentLine[c])) c++;

      if (c >= currentLine.length && l < buffer.length - 1) {
        l++;
        c = 0;
        const nextLine = buffer[l] || "";
        while (c < nextLine.length && /\s/.test(nextLine[c])) c++;
      }

      return { line: l, col: c };
    },
    [buffer],
  );

  const findWordEnd = useCallback(
    (line: number, col: number) => {
      const currentLine = buffer[line] || "";
      let c = col + 1;
      let l = line;

      if (c >= currentLine.length && l < buffer.length - 1) {
        l++;
        c = 0;
        const nextLine = buffer[l] || "";
        while (c < nextLine.length && /\s/.test(nextLine[c])) c++;
      }

      const targetLine = buffer[l] || "";
      while (c < targetLine.length && !/\s/.test(targetLine[c])) c++;

      return { line: l, col: Math.max(0, c - 1) };
    },
    [buffer],
  );

  const findPrevWordStart = useCallback(
    (line: number, col: number) => {
      let c = col - 1;
      let l = line;

      if (c < 0 && l > 0) {
        l--;
        c = (buffer[l]?.length || 1) - 1;
      }

      const currentLine = buffer[l] || "";
      while (c > 0 && /\s/.test(currentLine[c])) c--;
      while (c > 0 && !/\s/.test(currentLine[c - 1])) c--;

      return { line: l, col: Math.max(0, c) };
    },
    [buffer],
  );

  const deleteWord = useCallback(() => {
    const currentLine = buffer[cursor.line] || "";
    let endCol = cursor.col;

    while (endCol < currentLine.length && !/\s/.test(currentLine[endCol]))
      endCol++;
    while (endCol < currentLine.length && /\s/.test(currentLine[endCol]))
      endCol++;

    const newLine =
      currentLine.slice(0, cursor.col) + currentLine.slice(endCol);
    const newBuffer = [...buffer];
    newBuffer[cursor.line] = newLine;
    setBuffer(newBuffer);
    setCursor(clampCursor(cursor.line, cursor.col, newBuffer));
  }, [buffer, cursor, clampCursor]);

  const deleteLine = useCallback(() => {
    if (buffer.length === 1) {
      setBuffer([""]);
      setCursor({ line: 0, col: 0 });
      return;
    }

    const newBuffer = buffer.filter((_, i) => i !== cursor.line);
    const newLine = Math.min(cursor.line, newBuffer.length - 1);
    setBuffer(newBuffer);
    setCursor(clampCursor(newLine, 0, newBuffer));
  }, [buffer, cursor.line, clampCursor]);

  const deleteChar = useCallback(() => {
    const currentLine = buffer[cursor.line] || "";
    if (currentLine.length === 0) return;

    const newLine =
      currentLine.slice(0, cursor.col) + currentLine.slice(cursor.col + 1);
    const newBuffer = [...buffer];
    newBuffer[cursor.line] = newLine;
    setBuffer(newBuffer);
    setCursor(clampCursor(cursor.line, cursor.col, newBuffer));
  }, [buffer, cursor, clampCursor]);

  const executeVimCommand = useCallback((cmd: string) => {
    const trimmed = cmd.trim();

    switch (trimmed) {
      case "q":
      case "q!":
      case "wq":
      case "wq!":
      case "x":
        setView("shell");
        setShellHistory([]);
        break;
    }

    setCommandInput("");
    setMode("normal");
  }, []);

  const executeShellCommand = useCallback(
    (cmd: string) => {
      const trimmed = cmd.trim();
      const newHistory = [...shellHistory, `$ ${trimmed}`];

      switch (trimmed) {
        case "help":
          newHistory.push(SHELL_HELP);
          break;
        case "vim":
        case "nvim":
          setBuffer([""]);
          setCursor({ line: 0, col: 0 });
          setMode("normal");
          setView("vim");
          return;
        case "chroma":
          window.open("https://trychroma.com", "_blank");
          newHistory.push("Opening trychroma.com...");
          break;
        case "exit":
          onClose?.();
          return;
        case "":
          break;
        default:
          newHistory.push(`command not found: ${trimmed}`);
          newHistory.push(`Type 'help' for available commands.`);
      }

      setShellHistory(newHistory);
      setShellInput("");
    },
    [shellHistory, onClose],
  );

  const handleNormalMode = useCallback(
    (e: React.KeyboardEvent) => {
      const key = e.key;

      if (key === ":") {
        setMode("command");
        setCommandInput("");
        return;
      }

      if (pendingKey === "g") {
        if (key === "g") {
          setCursor({ line: 0, col: 0 });
        }
        setPendingKey(null);
        return;
      }

      if (pendingKey === "d") {
        if (key === "d") {
          deleteLine();
        } else if (key === "w") {
          deleteWord();
        }
        setPendingKey(null);
        return;
      }

      switch (key) {
        case "h":
        case "ArrowLeft":
          setCursor((c) => clampCursor(c.line, c.col - 1, buffer));
          break;
        case "j":
        case "ArrowDown":
          setCursor((c) => clampCursor(c.line + 1, c.col, buffer));
          break;
        case "k":
        case "ArrowUp":
          setCursor((c) => clampCursor(c.line - 1, c.col, buffer));
          break;
        case "l":
        case "ArrowRight":
          setCursor((c) => clampCursor(c.line, c.col + 1, buffer));
          break;
        case "g":
          setPendingKey("g");
          break;
        case "G":
          setCursor(clampCursor(buffer.length - 1, 0, buffer));
          break;
        case "w": {
          const next = findNextWordStart(cursor.line, cursor.col);
          setCursor(clampCursor(next.line, next.col, buffer));
          break;
        }
        case "e": {
          const end = findWordEnd(cursor.line, cursor.col);
          setCursor(clampCursor(end.line, end.col, buffer));
          break;
        }
        case "b": {
          const prev = findPrevWordStart(cursor.line, cursor.col);
          setCursor(clampCursor(prev.line, prev.col, buffer));
          break;
        }
        case "i":
          setMode("insert");
          break;
        case "a":
          setMode("insert");
          setCursor((c) => clampCursor(c.line, c.col + 1, buffer));
          break;
        case "x":
          deleteChar();
          break;
        case "d":
          setPendingKey("d");
          break;
      }
    },
    [
      buffer,
      cursor,
      pendingKey,
      clampCursor,
      findNextWordStart,
      findWordEnd,
      findPrevWordStart,
      deleteLine,
      deleteWord,
      deleteChar,
    ],
  );

  const handleInsertMode = useCallback(
    (e: React.KeyboardEvent) => {
      const key = e.key;

      if (key === "Escape") {
        setMode("normal");
        setCursor((c) => clampCursor(c.line, Math.max(0, c.col - 1), buffer));
        return;
      }

      if (key === "Backspace") {
        e.preventDefault();
        const currentLine = buffer[cursor.line] || "";

        if (cursor.col > 0) {
          const newLine =
            currentLine.slice(0, cursor.col - 1) +
            currentLine.slice(cursor.col);
          const newBuffer = [...buffer];
          newBuffer[cursor.line] = newLine;
          setBuffer(newBuffer);
          setCursor((c) => ({ ...c, col: c.col - 1 }));
        } else if (cursor.line > 0) {
          const prevLine = buffer[cursor.line - 1] || "";
          const newCol = prevLine.length;
          const newBuffer = [...buffer];
          newBuffer[cursor.line - 1] = prevLine + currentLine;
          newBuffer.splice(cursor.line, 1);
          setBuffer(newBuffer);
          setCursor({ line: cursor.line - 1, col: newCol });
        }
        return;
      }

      if (key === "Delete") {
        e.preventDefault();
        const currentLine = buffer[cursor.line] || "";

        if (cursor.col < currentLine.length) {
          const newLine =
            currentLine.slice(0, cursor.col) +
            currentLine.slice(cursor.col + 1);
          const newBuffer = [...buffer];
          newBuffer[cursor.line] = newLine;
          setBuffer(newBuffer);
        } else if (cursor.line < buffer.length - 1) {
          const nextLine = buffer[cursor.line + 1] || "";
          const newBuffer = [...buffer];
          newBuffer[cursor.line] = currentLine + nextLine;
          newBuffer.splice(cursor.line + 1, 1);
          setBuffer(newBuffer);
        }
        return;
      }

      if (key === "Enter") {
        e.preventDefault();
        const currentLine = buffer[cursor.line] || "";
        const beforeCursor = currentLine.slice(0, cursor.col);
        const afterCursor = currentLine.slice(cursor.col);
        const newBuffer = [...buffer];
        newBuffer[cursor.line] = beforeCursor;
        newBuffer.splice(cursor.line + 1, 0, afterCursor);
        setBuffer(newBuffer);
        setCursor({ line: cursor.line + 1, col: 0 });
        return;
      }

      if (key === "ArrowLeft") {
        e.preventDefault();
        setCursor((c) => clampCursor(c.line, c.col - 1, buffer));
        return;
      }

      if (key === "ArrowRight") {
        e.preventDefault();
        setCursor((c) => clampCursor(c.line, c.col + 1, buffer));
        return;
      }

      if (key === "ArrowUp") {
        e.preventDefault();
        setCursor((c) => clampCursor(c.line - 1, c.col, buffer));
        return;
      }

      if (key === "ArrowDown") {
        e.preventDefault();
        setCursor((c) => clampCursor(c.line + 1, c.col, buffer));
        return;
      }

      if (key.length === 1) {
        e.preventDefault();
        const currentLine = buffer[cursor.line] || "";
        const newLine =
          currentLine.slice(0, cursor.col) +
          key +
          currentLine.slice(cursor.col);
        const newBuffer = [...buffer];
        newBuffer[cursor.line] = newLine;
        setBuffer(newBuffer);
        setCursor((c) => ({ ...c, col: c.col + 1 }));
      }
    },
    [buffer, cursor, clampCursor],
  );

  const handleCommandMode = useCallback(
    (e: React.KeyboardEvent) => {
      const key = e.key;

      if (key === "Escape") {
        setMode("normal");
        setCommandInput("");
        return;
      }

      if (key === "Enter") {
        executeVimCommand(commandInput);
        return;
      }

      if (key === "Backspace") {
        e.preventDefault();
        if (commandInput.length === 0) {
          setMode("normal");
        } else {
          setCommandInput((c) => c.slice(0, -1));
        }
        return;
      }

      if (key.length === 1) {
        e.preventDefault();
        setCommandInput((c) => c + key);
      }
    },
    [commandInput, executeVimCommand],
  );

  const handleShellKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      const key = e.key;

      if (key === "Enter") {
        e.preventDefault();
        executeShellCommand(shellInput);
        return;
      }

      if (key === "Backspace") {
        e.preventDefault();
        setShellInput((c) => c.slice(0, -1));
        return;
      }

      if (key.length === 1) {
        e.preventDefault();
        setShellInput((c) => c + key);
      }
    },
    [shellInput, executeShellCommand],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (view === "shell") {
        handleShellKeyDown(e);
        return;
      }

      if (mode === "normal") {
        e.preventDefault();
        handleNormalMode(e);
      } else if (mode === "insert") {
        handleInsertMode(e);
      } else if (mode === "command") {
        handleCommandMode(e);
      }
    },
    [
      view,
      mode,
      handleNormalMode,
      handleInsertMode,
      handleCommandMode,
      handleShellKeyDown,
    ],
  );

  useEffect(() => {
    containerRef.current?.focus();
  }, []);

  useEffect(() => {
    containerRef.current?.focus();
  }, [view]);

  const lineNumberWidth = String(buffer.length).length;

  if (view === "shell") {
    return (
      <div
        ref={containerRef}
        className="flex flex-col h-full bg-white text-black font-mono text-sm outline-none"
        tabIndex={0}
        onKeyDown={handleKeyDown}
      >
        <div className="flex-1 overflow-auto p-2">
          <div className="text-gray-500 mb-2">
            Type &apos;help&apos; for available commands.
          </div>
          {shellHistory.map((line, i) => (
            <div key={i} className="whitespace-pre-wrap">
              {line}
            </div>
          ))}
          <div className="flex items-center">
            <span className="text-green-600 mr-[.75ch]">$ </span>
            <span>{shellInput}</span>
            <span className="w-[2px] h-[1.2em] bg-black animate-pulse ml-px" />
          </div>
          <div ref={shellEndRef} />
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="flex flex-col h-full bg-white text-black font-mono text-sm outline-none"
      tabIndex={0}
      onKeyDown={handleKeyDown}
    >
      <div className="flex-1 overflow-auto">
        {buffer.map((line, lineIndex) => (
          <div
            key={lineIndex}
            ref={(el) => {
              if (el) lineRefs.current.set(lineIndex, el);
            }}
            className="flex"
          >
            <span
              className="text-gray-400 select-none pr-3 text-right"
              style={{ minWidth: `${lineNumberWidth + 2}ch` }}
            >
              {lineIndex + 1}
            </span>
            <span className="whitespace-pre flex-1">
              {lineIndex === cursor.line ? (
                <>
                  {line.slice(0, cursor.col)}
                  <span
                    className={
                      mode === "normal"
                        ? "bg-black text-white"
                        : "border-l-2 border-black"
                    }
                  >
                    {mode === "normal" ? line[cursor.col] || " " : ""}
                  </span>
                  {line.slice(mode === "normal" ? cursor.col + 1 : cursor.col)}
                </>
              ) : (
                line || " "
              )}
            </span>
          </div>
        ))}
      </div>

      <div className="border-t border-gray-200 px-2 py-1 flex justify-between text-xs text-gray-600">
        {mode === "command" ? (
          <span className="font-bold">
            :{commandInput}
            <span className="animate-pulse">▌</span>
          </span>
        ) : (
          <span className="font-bold">
            -- {mode.toUpperCase()} --
            {pendingKey && <span className="ml-2">{pendingKey}</span>}
          </span>
        )}
        <span>
          {cursor.line + 1}:{cursor.col + 1}
        </span>
      </div>
    </div>
  );
}
