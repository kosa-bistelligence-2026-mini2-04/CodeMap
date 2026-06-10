"use client";

import { PaymentMethodsPanel } from "@/components/billing";
import { PageHero } from "@/components/dashboard/page-hero";

export default function PaymentMethodsPage() {
  return (
    <div className="mx-auto w-full max-w-5xl space-y-8">
      <PageHero
        eyebrow="Billing · Payment methods"
        title={
          <>
            Cards on <em>file.</em>
          </>
        }
        description="Cards and bank accounts you can charge are managed in the Stripe billing portal — open it to add, remove, or set a default."
      />
      <PaymentMethodsPanel />
    </div>
  );
}
