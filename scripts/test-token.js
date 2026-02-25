// Test GitHub token
const TOKEN = "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";

async function test() {
  console.log("[v0] Token length:", TOKEN.length);
  console.log("[v0] Token starts with:", TOKEN.substring(0, 4));
  
  // Test 1: Check user identity
  const res1 = await fetch("https://api.github.com/user", {
    headers: {
      Authorization: `Bearer ${TOKEN}`,
      Accept: "application/vnd.github.v3+json",
      "User-Agent": "v0-projectx-fix",
    },
  });
  console.log("[v0] /user status:", res1.status);
  const body1 = await res1.text();
  console.log("[v0] /user response:", body1.substring(0, 300));

  // Test 2: Check repo access
  const res2 = await fetch("https://api.github.com/repos/MikeyRock/projectx-bch-solo", {
    headers: {
      Authorization: `Bearer ${TOKEN}`,
      Accept: "application/vnd.github.v3+json",
      "User-Agent": "v0-projectx-fix",
    },
  });
  console.log("[v0] /repos status:", res2.status);
  const body2 = await res2.text();
  console.log("[v0] /repos response:", body2.substring(0, 300));
}

test().catch(e => console.error("[v0] Error:", e.message));
