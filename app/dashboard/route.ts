import { readFileSync } from "fs";
import path from "path";
import { NextResponse } from "next/server";

export function GET() {
  const html = readFileSync(
    path.join(process.cwd(), "projectx-bch-solo/exports/app/index.html"),
    "utf8"
  );
  return new NextResponse(html, {
    headers: { "Content-Type": "text/html; charset=utf-8" },
  });
}
