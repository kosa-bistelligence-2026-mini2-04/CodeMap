import { NextRequest, NextResponse } from "next/server";

type GitHubRepository = {
  id: number;
  name: string;
  full_name: string;
  html_url: string;
  description: string | null;
  language: string | null;
  stargazers_count: number;
  owner: {
    avatar_url: string;
  };
};

export async function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.get("q")?.trim() || "";
  if (query.length < 2 || query.length > 100) {
    return NextResponse.json({ items: [] });
  }

  const token = process.env.GITHUB_TOKEN || process.env.GITHUB_API_TOKEN;
  const publicHeaders: HeadersInit = {
    Accept: "application/vnd.github+json",
    "User-Agent": "CodeMap-AI",
    "X-GitHub-Api-Version": "2022-11-28",
  };
  const headers: HeadersInit = token
    ? { ...publicHeaders, Authorization: `Bearer ${token}` }
    : publicHeaders;

  const searchParams = new URLSearchParams({
    q: `${query} in:name,description`,
    sort: "stars",
    order: "desc",
    per_page: "6",
  });

  try {
    const endpoint = `https://api.github.com/search/repositories?${searchParams}`;
    let response = await fetch(endpoint, {
      headers,
      cache: "no-store",
    });

    if (response.status === 401 && token) {
      response = await fetch(endpoint, { headers: publicHeaders, cache: "no-store" });
    }

    if (!response.ok) {
      return NextResponse.json(
        { items: [], error: response.status === 403 ? "rate_limited" : "github_unavailable", upstreamStatus: response.status },
        { status: response.status === 403 ? 429 : 502 },
      );
    }

    const payload = (await response.json()) as { items?: GitHubRepository[] };
    const items = (payload.items || []).map((repo) => ({
      id: repo.id,
      name: repo.name,
      fullName: repo.full_name,
      url: repo.html_url,
      description: repo.description,
      language: repo.language,
      stars: repo.stargazers_count,
      ownerAvatar: repo.owner.avatar_url,
    }));

    return NextResponse.json(
      { items },
      { headers: { "Cache-Control": "private, max-age=60" } },
    );
  } catch {
    return NextResponse.json({ items: [], error: "github_unavailable" }, { status: 502 });
  }
}
