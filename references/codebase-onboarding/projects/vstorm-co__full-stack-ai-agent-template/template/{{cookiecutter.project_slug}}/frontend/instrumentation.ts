{%- if cookiecutter.enable_logfire %}
import { registerOTel } from "@vercel/otel";

export function register() {
  registerOTel({
    serviceName: "{{ cookiecutter.project_slug }}-frontend",
  });
}
{%- else %}
// Logfire/OpenTelemetry instrumentation is disabled
export function register() {
  // No-op when Logfire is disabled
}
{%- endif %}
