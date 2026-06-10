"use client";

import { InvoicesPanel } from "@/components/billing";
import { PageHero } from "@/components/dashboard/page-hero";

export default function InvoicesPage() {
  return (
    <div className="mx-auto w-full max-w-5xl space-y-8">
      <PageHero
        eyebrow="Billing · Invoices"
        title={
          <>
            Billing <em>history.</em>
          </>
        }
        description="Every invoice sent to this workspace, with a download link straight to the Stripe-hosted PDF."
      />
      <InvoicesPanel />
    </div>
  );
}
