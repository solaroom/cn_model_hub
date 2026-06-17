import { createRouter, createWebHistory } from "vue-router";
import { routes as autoRoutes } from "vue-router/auto-routes";

const repoRouteTypes = ["models", "datasets", "spaces"];

const repoRouteComponents = {
  index: () => import("@/pages/[type]s/[namespace]/[name]/index.vue"),
  tree: () =>
    import("@/pages/[type]s/[namespace]/[name]/tree/[branch]/index.vue"),
  treePath: () =>
    import("@/pages/[type]s/[namespace]/[name]/tree/[branch]/[...path].vue"),
  blob: () =>
    import("@/pages/[type]s/[namespace]/[name]/blob/[branch]/[...file].vue"),
  commit: () =>
    import("@/pages/[type]s/[namespace]/[name]/commit/[commit_id].vue"),
  commits: () =>
    import("@/pages/[type]s/[namespace]/[name]/commits/[branch]/index.vue"),
  edit: () =>
    import("@/pages/[type]s/[namespace]/[name]/edit/[branch]/[...file].vue"),
  settings: () => import("@/pages/[type]s/[namespace]/[name]/settings.vue"),
  upload: () =>
    import("@/pages/[type]s/[namespace]/[name]/upload/[branch].vue"),
};

function createRepoRoutes() {
  return repoRouteTypes.flatMap((type) => [
    {
      path: `/${type}/:namespace/:name`,
      component: repoRouteComponents.index,
    },
    {
      path: `/${type}/:namespace/:name/tree/:branch`,
      component: repoRouteComponents.tree,
    },
    {
      path: `/${type}/:namespace/:name/tree/:branch/:path(.*)`,
      component: repoRouteComponents.treePath,
    },
    {
      path: `/${type}/:namespace/:name/blob/:branch/:file(.*)`,
      component: repoRouteComponents.blob,
    },
    {
      path: `/${type}/:namespace/:name/commit/:commit_id`,
      component: repoRouteComponents.commit,
    },
    {
      path: `/${type}/:namespace/:name/commits/:branch`,
      component: repoRouteComponents.commits,
    },
    {
      path: `/${type}/:namespace/:name/edit/:branch/:file(.*)`,
      component: repoRouteComponents.edit,
    },
    {
      path: `/${type}/:namespace/:name/settings`,
      component: repoRouteComponents.settings,
    },
    {
      path: `/${type}/:namespace/:name/upload/:branch`,
      component: repoRouteComponents.upload,
    },
  ]);
}

const generatedRoutes = Array.isArray(autoRoutes) ? autoRoutes : [];

export const routes = [...createRepoRoutes(), ...generatedRoutes];

export function createAppRouter() {
  return createRouter({
    history: createWebHistory(),
    routes,
  });
}
