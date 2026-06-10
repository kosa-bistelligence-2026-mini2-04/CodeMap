import type { z } from "zod";

export interface FeatureResult {
  success: boolean;
  data?: unknown;
  message?: string;
  error?: string;
}

export interface Feature<TInput extends z.ZodType = z.ZodType> {
  name: string;
  description: string;
  schema: TInput;
  execute: (input: z.infer<TInput>) => FeatureResult | Promise<FeatureResult>;
}
