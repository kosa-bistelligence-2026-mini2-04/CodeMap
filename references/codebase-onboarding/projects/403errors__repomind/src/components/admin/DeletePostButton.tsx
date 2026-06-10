"use client";

import { Trash2 } from "lucide-react";
import { deletePostAction } from "@/app/admin/blog/actions";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { ConfirmDialog } from "@/components/ConfirmDialog";

interface DeletePostButtonProps {
  id: string;
  title: string;
}

export function DeletePostButton({ id, title }: DeletePostButtonProps) {
  const [isDeleting, setIsDeleting] = useState(false);
  const [isConfirmOpen, setIsConfirmOpen] = useState(false);
  const router = useRouter();

  const handleDelete = async () => {
    console.log("Starting deletion for:", id);
    setIsDeleting(true);
    try {
      await deletePostAction(id);
      console.log("Deletion successful");
      router.refresh();
    } catch (error) {
      console.error("Failed to delete post:", error);
      alert("Failed to delete post. Please try again.");
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setIsConfirmOpen(true)}
        disabled={isDeleting}
        className={`p-1.5 rounded-lg transition-all ${
          isDeleting
            ? "bg-red-500/20 text-red-400 opacity-50 cursor-wait"
            : "text-zinc-500 hover:text-red-400 hover:bg-red-400/5 text-sm cursor-pointer"
        }`}
        title="Delete Post"
      >
        <Trash2 size={16} />
      </button>

      <ConfirmDialog
        isOpen={isConfirmOpen}
        title="Delete post?"
        message={`This will permanently delete \"${title}\". This cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        confirmVariant="danger"
        onConfirm={handleDelete}
        onCancel={() => setIsConfirmOpen(false)}
      />
    </>
  );
}
