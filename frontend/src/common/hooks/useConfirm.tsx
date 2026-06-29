"use client";

import { useCallback, useState } from "react";
import { AlertTriangle } from "lucide-react";

type ConfirmDialogState = {
  title: string;
  message: string;
  onConfirm: () => void;
  onCancel?: () => void;
};

interface ConfirmDialogProps {
  isDark: boolean;
  isKo: boolean;
}

export function useConfirm() {
  const [dialog, setDialog] = useState<ConfirmDialogState | null>(null);

  const confirm = useCallback((
    title: string,
    message: string,
    showCancel: boolean = true,
  ) => new Promise<boolean>((resolve) => {
    setDialog({
      title,
      message,
      onConfirm: () => {
        setDialog(null);
        resolve(true);
      },
      onCancel: showCancel ? () => {
        setDialog(null);
        resolve(false);
      } : undefined,
    });
  }), []);

  const ConfirmDialog = useCallback(({ isDark, isKo }: ConfirmDialogProps) => {
    if (!dialog) return null;
    return (
      <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
        <div className={`w-full max-w-sm rounded-2xl border p-5 shadow-2xl ${isDark ? "border-zinc-800 bg-zinc-900" : "border-zinc-200 bg-white"}`}>
          <div className="flex items-start gap-3">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-full bg-amber-500/10 text-amber-500">
              <AlertTriangle className="size-5" />
            </div>
            <div>
              <h3 className={`text-base font-bold ${isDark ? "text-white" : "text-zinc-900"}`}>{dialog.title}</h3>
              <p className={`mt-1 whitespace-pre-wrap text-sm leading-relaxed ${isDark ? "text-zinc-400" : "text-zinc-600"}`}>
                {dialog.message}
              </p>
            </div>
          </div>
          <div className="mt-6 flex justify-end gap-2">
            {dialog.onCancel && (
              <button
                onClick={dialog.onCancel}
                className={`rounded-lg px-4 py-2 text-sm font-semibold transition ${isDark ? "text-zinc-300 hover:bg-zinc-800" : "text-zinc-600 hover:bg-zinc-100"}`}
              >
                {isKo ? "취소" : "Cancel"}
              </button>
            )}
            <button
              onClick={dialog.onConfirm}
              className="rounded-lg bg-blue-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-600"
            >
              {isKo ? "확인" : "Confirm"}
            </button>
          </div>
        </div>
      </div>
    );
  }, [dialog]);

  return { confirm, ConfirmDialog };
}
