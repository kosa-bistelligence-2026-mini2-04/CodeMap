import type { ArgsDef, ArgDef } from "citty";
import type { z } from "zod";

/**
 * Convert Zod schema to citty ArgsDef
 */
export function zodToCittyArgs(schema: z.ZodType): ArgsDef {
  // Handle ZodObject
  if ("shape" in schema && typeof schema.shape === "object") {
    const shape = schema.shape as Record<string, z.ZodType>;
    const args: ArgsDef = {};

    for (const [key, fieldSchema] of Object.entries(shape)) {
      const description = getZodDescription(fieldSchema);
      const isOptional = isZodOptional(fieldSchema);
      const defaultValue = getZodDefault(fieldSchema);
      const zodType = getZodBaseType(fieldSchema);

      args[key] = createArgDef(zodType, description, isOptional, defaultValue);
    }

    return args;
  }

  return {};
}

function createArgDef(
  zodType: string,
  description: string | undefined,
  isOptional: boolean,
  defaultValue: unknown,
): ArgDef {
  const required = !isOptional && defaultValue === undefined;

  if (zodType === "boolean") {
    const arg: ArgDef = {
      type: "boolean" as const,
      required,
    };
    if (description !== undefined) {
      arg.description = description;
    }
    if (defaultValue !== undefined) {
      arg.default = defaultValue as boolean;
    }
    return arg;
  }

  // String, Number, Enum all become string in citty
  const arg: ArgDef = {
    type: "string" as const,
    required,
  };
  if (description !== undefined) {
    arg.description = description;
  }
  if (defaultValue !== undefined) {
    arg.default = defaultValue as string;
  }
  return arg;
}

function getZodDescription(schema: z.ZodType): string | undefined {
  if ("description" in schema && typeof schema.description === "string") {
    return schema.description;
  }
  // Check inner type for optional/default wrappers

  if ("_def" in schema) {
    // eslint-disable-next-line @typescript-eslint/no-deprecated
    const def = schema._def as unknown as Record<string, unknown>;
    if ("description" in def && typeof def.description === "string") {
      return def.description;
    }
    if ("innerType" in def && def.innerType !== undefined) {
      return getZodDescription(def.innerType as z.ZodType);
    }
  }
  return undefined;
}

function isZodOptional(schema: z.ZodType): boolean {
  if ("_def" in schema) {
    // eslint-disable-next-line @typescript-eslint/no-deprecated
    const def = schema._def as unknown as Record<string, unknown>;
    if (def.type === "optional" || def.type === "default") {
      return true;
    }
  }
  return false;
}

function getZodDefault(schema: z.ZodType): unknown {
  if ("_def" in schema) {
    // eslint-disable-next-line @typescript-eslint/no-deprecated
    const def = schema._def as unknown as Record<string, unknown>;
    if (def.type === "default" && "defaultValue" in def) {
      return def.defaultValue;
    }
  }
  return undefined;
}

function getZodBaseType(schema: z.ZodType): string {
  if ("_def" in schema) {
    // eslint-disable-next-line @typescript-eslint/no-deprecated
    const def = schema._def as unknown as Record<string, unknown>;
    const type = def.type as string;

    if (type === "optional" || type === "default") {
      if ("innerType" in def && def.innerType !== undefined) {
        return getZodBaseType(def.innerType as z.ZodType);
      }
    }

    return type;
  }
  return "string";
}
