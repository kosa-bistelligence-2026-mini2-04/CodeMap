"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { apiClient } from "@/lib/api-client";
import type {
  CheckoutSessionResponse,
  PortalSessionResponse,
  CreateCheckoutInput,
  SubscriptionRead,
  CreditBalanceRead,
  CreditTransactionList,
  PlanRead,
  InvoiceList,
  InvoiceRead,
} from "@/types";

export function useBilling() {
  const [isLoading, setIsLoading] = useState(false);

  const startCheckout = useCallback(async (input: CreateCheckoutInput) => {
    setIsLoading(true);
    try {
      const { url } = await apiClient.post<CheckoutSessionResponse>("/billing/checkout", input);
      window.location.href = url;
    } catch {
      toast.error("Failed to start checkout");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const openPortal = useCallback(async () => {
    setIsLoading(true);
    try {
      const { url } = await apiClient.post<PortalSessionResponse>("/billing/portal");
      window.location.href = url;
    } catch {
      toast.error("Failed to open billing portal");
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { isLoading, startCheckout, openPortal };
}

export function useSubscription() {
  const [subscription, setSubscription] = useState<SubscriptionRead | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSubscription = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.get<SubscriptionRead>("/billing/me/subscription");
      setSubscription(data);
    } catch {
      setSubscription(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const cancelSubscription = useCallback(async () => {
    try {
      await apiClient.delete("/billing/me/subscription");
      toast.success("Subscription will cancel at the end of the billing period.");
      await fetchSubscription();
    } catch {
      toast.error("Failed to cancel subscription");
    }
  }, [fetchSubscription]);

  const reactivateSubscription = useCallback(async () => {
    try {
      await apiClient.post("/billing/me/subscription/reactivate");
      toast.success("Subscription reactivated.");
      await fetchSubscription();
    } catch {
      toast.error("Failed to reactivate subscription");
    }
  }, [fetchSubscription]);

  const updateSeats = useCallback(
    async (seats: number) => {
      try {
        await apiClient.patch("/billing/me/subscription", { seats_quantity: seats });
        toast.success("Seats updated.");
        await fetchSubscription();
      } catch {
        toast.error("Failed to update seats");
      }
    },
    [fetchSubscription],
  );

  useEffect(() => {
    fetchSubscription();
  }, [fetchSubscription]);

  return {
    subscription,
    isLoading,
    error,
    fetchSubscription,
    cancelSubscription,
    reactivateSubscription,
    updateSeats,
  };
}

export function useInvoices() {
  const [invoices, setInvoices] = useState<InvoiceRead[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchInvoices = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await apiClient.get<InvoiceList>("/billing/me/invoices");
      setInvoices(data.items);
    } catch {
      setInvoices([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchInvoices();
  }, [fetchInvoices]);

  return { invoices, isLoading, fetchInvoices };
}

export function useCredits() {
  const [balance, setBalance] = useState<CreditBalanceRead | null>(null);
  const [transactions, setTransactions] = useState<CreditTransactionList | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [txLoading, setTxLoading] = useState(false);

  const fetchBalance = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await apiClient.get<CreditBalanceRead>("/billing/me/credits");
      setBalance(data);
    } catch {
      setBalance(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const fetchTransactions = useCallback(async (skip = 0, limit = 20) => {
    setTxLoading(true);
    try {
      const data = await apiClient.get<CreditTransactionList>(
        `/billing/me/credits/transactions?skip=${skip}&limit=${limit}`,
      );
      setTransactions(data);
    } catch {
      setTransactions(null);
    } finally {
      setTxLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBalance();
    fetchTransactions();
  }, [fetchBalance, fetchTransactions]);

  // Listen for billing-affecting events (e.g. a finished chat turn) and
  // refetch the balance so the UI doesn't show stale numbers.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const handler = () => {
      fetchBalance();
      fetchTransactions();
    };
    window.addEventListener("billing:refresh", handler);
    return () => window.removeEventListener("billing:refresh", handler);
  }, [fetchBalance, fetchTransactions]);

  return { balance, transactions, isLoading, txLoading, fetchBalance, fetchTransactions };
}

export function usePlans() {
  const [plans, setPlans] = useState<PlanRead[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    apiClient
      .get<{ items: PlanRead[]; total: number }>("/billing/plans")
      .then((data) => setPlans(data.items))
      .catch(() => setPlans([]))
      .finally(() => setIsLoading(false));
  }, []);

  return { plans, isLoading };
}
