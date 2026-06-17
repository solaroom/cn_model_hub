import { describe, expect, it } from "vitest";

const { routes } = await import("@/router");

function matchPath(path) {
  return routes.find((route) => {
    if (route.path === path) return true;

    const pattern = route.path
      .replace(/:[^/]+\(.\*\)/g, ".+")
      .replace(/:[^/]+/g, "[^/]+");
    return new RegExp(`^${pattern}$`).test(path);
  });
}

describe("app router", () => {
  it("matches repository tree URLs before generated catch-all user routes", () => {
    const route = matchPath("/models/user1/tiny-qwen2-no-app/tree/main");

    expect(route?.path).toBe("/models/:namespace/:name/tree/:branch");
  });

  it("registers explicit routes for each repository type", () => {
    const paths = routes.map((route) => route.path);

    expect(paths).toContain("/models/:namespace/:name");
    expect(paths).toContain("/datasets/:namespace/:name");
    expect(paths).toContain("/spaces/:namespace/:name");
  });
});
