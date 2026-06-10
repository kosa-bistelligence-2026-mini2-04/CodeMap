import ora, { type Ora } from "ora";

/**
 * Create a spinner with consistent styling
 */
export function createSpinner(text: string): Ora {
  return ora({
    text,
    spinner: "dots",
  });
}

/**
 * Run an async function with a spinner
 * Shows the spinner while the function is running, then shows success/failure
 */
export async function withSpinner<T>(
  text: string,
  fn: () => Promise<T>,
  successText?: string,
): Promise<T> {
  // Skip spinner in non-TTY environments (CI, pipes, etc.)
  if (!process.stdout.isTTY) {
    // eslint-disable-next-line no-console
    console.log(text);
    const result = await fn();
    // eslint-disable-next-line no-console
    console.log(successText ?? "Done");
    return result;
  }

  const spinner = createSpinner(text).start();
  try {
    const result = await fn();
    spinner.succeed(successText ?? text);
    return result;
  } catch (error) {
    spinner.fail();
    throw error;
  }
}
