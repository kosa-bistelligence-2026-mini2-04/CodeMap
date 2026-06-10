import { registerOTel } from "@vercel/otel";

export function register() {
  if (process.env.VERCEL) {
    registerOTel({ serviceName: "github-chat-app" });
  }
}
