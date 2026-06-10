export type { Feature, FeatureResult } from "@features/types";

export interface ServerConfig {
  name: string;
  fullName: string;
  version: string;
  description?: string;
}

export interface CLICommand {
  name: string;
  description: string;
  options?: CLIOption[];
  action: (args: string[], options: Record<string, string | boolean>) => void;
}

export interface CLIOption {
  flag: string;
  description: string;
  required?: boolean;
  defaultValue?: string;
}
