import type { Metadata } from "next";
{%- if cookiecutter.enable_embed_mode %}
import { notFound } from "next/navigation";
{%- endif %}

import { LoginForm } from "@/components/auth";
import type { Locale } from "@/i18n";
import { pageMetadata } from "@/lib/seo";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return pageMetadata({
    title: "Sign in",
    description: "Sign in to your workspace.",
    path: "/login",
    locale,
    noindex: true,
  });
}

export default function LoginPage() {
{%- if cookiecutter.enable_embed_mode %}
  notFound();
{%- endif %}
  return <LoginForm />;
}
