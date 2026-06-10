"use server";

import { refreshCatalogCache } from "@/lib/repo-catalog";
import { auth } from "@/lib/auth";
import { isAdminUser } from "@/lib/admin-auth";
import { revalidatePath } from "next/cache";

async function checkAdmin() {
  const session = await auth();
  if (!isAdminUser(session)) {
    throw new Error("Unauthorized");
  }
}

export async function refreshCatalogAction() {
  await checkAdmin();
  
  // Clear the next.js cache for the repo catalog
  await refreshCatalogCache();
  
  // Revalidate the admin index page to show fresh data
  revalidatePath("/admin/index");
  
  return { success: true };
}
