"use client";

import { useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { Check } from "lucide-react";
import { toast } from "sonner";

import { SubscriptionPanel } from "@/components/billing";
import { PageHero } from "@/components/dashboard/page-hero";
import { LoadingState } from "@/components/states";
import { useBilling, usePlans } from "@/hooks";
import { cn } from "@/lib/utils";

function formatMoney(cents: number, currency: string) {
  return (cents / 100).toLocaleString("en-US", {
    style: "currency",
    currency: currency.toUpperCase(),
    minimumFractionDigits: 0,
  });
}

export default function SubscriptionPage() {
  const searchParams = useSearchParams();
  const { plans, isLoading: plansLoading } = usePlans();
  const { startCheckout, isLoading: checkoutLoading } = useBilling();

  useEffect(() => {
    if (searchParams.get("success") === "1") {
      toast.success("Subscription updated successfully!");
    }
  }, [searchParams]);

  return (
    <div className="mx-auto w-full max-w-5xl space-y-8">
      <PageHero
        eyebrow="Billing · Subscription"
        title={
          <>
            Manage your <em>plan.</em>
          </>
        }
        description="Upgrade, downgrade, or pick a different billing interval. Changes take effect on the next billing cycle."
      />

      <SubscriptionPanel />

      <section className="space-y-3">
        <div>
          <p className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
            Available plans
          </p>
          <h2 className="font-display text-foreground text-xl font-semibold tracking-tight">
            Switch plan
          </h2>
        </div>

        {plansLoading ? (
          <LoadingState variant="skeleton-cards" rows={3} />
        ) : plans.length === 0 ? (
          <p className="text-foreground/55 text-sm">No alternative plans configured.</p>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {plans.map((plan) => {
              const activePrices = plan.prices.filter((p) => p.is_active);
              return (
                <article
                  key={plan.id}
                  className={cn(
                    "border-border bg-card flex flex-col rounded-2xl border p-5 transition-colors",
                    plan.is_active ? "ring-brand/40 ring-2" : "hover:border-foreground/20",
                  )}
                >
                  <header className="space-y-1.5">
                    <div className="flex items-center justify-between gap-2">
                      <h3 className="text-foreground text-base font-semibold">
                        {plan.display_name}
                      </h3>
                      {plan.is_active && (
                        <span className="bg-brand/15 text-foreground rounded-full px-2 py-0.5 text-[10px] font-medium tracking-wide uppercase">
                          Current
                        </span>
                      )}
                    </div>
                    {plan.description && (
                      <p className="text-foreground/60 text-xs leading-relaxed">
                        {plan.description}
                      </p>
                    )}
                  </header>

                  <ul className="text-foreground/70 my-5 space-y-1.5 text-sm">
                    {activePrices.map((price) => (
                      <li key={price.id} className="flex items-baseline justify-between gap-2">
                        <span className="text-foreground/55 capitalize">{price.interval}</span>
                        <span className="text-foreground font-mono tabular-nums">
                          {formatMoney(price.amount_cents, price.currency)}
                        </span>
                      </li>
                    ))}
                    {plan.monthly_credits_base > 0 && (
                      <li className="text-foreground/60 flex items-center gap-1.5 pt-1 text-xs">
                        <Check className="h-3.5 w-3.5" />
                        {plan.monthly_credits_base.toLocaleString()} credits / month
                      </li>
                    )}
                  </ul>

                  <div className="mt-auto space-y-2">
                    {activePrices.map((price) => (
                      <button
                        key={price.id}
                        type="button"
                        disabled={checkoutLoading}
                        onClick={() =>
                          startCheckout({
                            price_id: price.id,
                            success_url: window.location.href + "?success=1",
                            cancel_url: window.location.href,
                          })
                        }
                        className="border-foreground/15 hover:border-foreground/40 text-foreground inline-flex w-full items-center justify-center rounded-full border px-4 py-2 text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        Choose {price.interval === "month" ? "monthly" : "annual"}
                      </button>
                    ))}
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
