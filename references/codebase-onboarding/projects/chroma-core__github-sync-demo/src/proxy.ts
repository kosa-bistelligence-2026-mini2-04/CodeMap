import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function proxy(req: NextRequest) {
  if (req.nextUrl.pathname === req.nextUrl.pathname.toLowerCase())
    return NextResponse.next();

  return NextResponse.redirect(
    new URL(
      req.nextUrl.origin +
        req.nextUrl.pathname.toLowerCase() +
        req.nextUrl.search,
    ),
  );
}
