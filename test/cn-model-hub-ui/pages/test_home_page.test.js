import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "@/testing/msw";
import { ElementPlusStubs, RouterLinkStub } from "../helpers/vue";
import { cloneFixture, jsonResponse, uiApiFixtures } from "../helpers/api-fixtures";
import { server } from "../setup/msw-server";

const mocks = vi.hoisted(() => ({
  router: {
    push: vi.fn(),
    replace: vi.fn(),
  },
  route: {
    params: {},
    query: {},
  },
  repoSortPreference: {
    getRepoSortPreference: vi.fn(),
    setRepoSortPreference: vi.fn(),
  },
  elMessage: {
    error: vi.fn(),
  },
}));

vi.mock("vue-router/auto", () => ({
  useRouter: () => mocks.router,
  useRoute: () => mocks.route,
}));

vi.mock("@/utils/repoSortPreference", () => ({
  getRepoSortPreference: mocks.repoSortPreference.getRepoSortPreference,
  setRepoSortPreference: mocks.repoSortPreference.setRepoSortPreference,
}));

vi.mock("element-plus", () => ({
  ElMessage: mocks.elMessage,
}));

import HomePage from "@/pages/index.vue";

describe("home page", () => {
  const requests = [];

  function installHandlers({
    modelRepos = [cloneFixture(uiApiFixtures.repo.info)],
    datasetRepos = cloneFixture(uiApiFixtures.userOverview.datasets),
    spaceRepos = cloneFixture(uiApiFixtures.userOverview.spaces),
  } = {}) {
    requests.length = 0;

    server.use(
      http.get("/api/models", ({ request }) => {
        const url = new URL(request.url);
        requests.push({
          type: "model",
          params: Object.fromEntries(url.searchParams.entries()),
        });
        return jsonResponse(modelRepos);
      }),
      http.get("/api/datasets", ({ request }) => {
        const url = new URL(request.url);
        requests.push({
          type: "dataset",
          params: Object.fromEntries(url.searchParams.entries()),
        });
        return jsonResponse(datasetRepos);
      }),
      http.get("/api/spaces", ({ request }) => {
        const url = new URL(request.url);
        requests.push({
          type: "space",
          params: Object.fromEntries(url.searchParams.entries()),
        });
        return jsonResponse(spaceRepos);
      }),
    );
  }

  beforeEach(() => {
    vi.clearAllMocks();
    setActivePinia(createPinia());
    mocks.route.query = {};
    mocks.repoSortPreference.getRepoSortPreference.mockReturnValue("trending");
    installHandlers();
  });

  function mountPage() {
    return mount(HomePage, {
      global: {
        mocks: {
          $router: mocks.router,
        },
        stubs: {
          ...ElementPlusStubs,
          RouterLink: RouterLinkStub,
        },
      },
    });
  }

  function findButtonByText(wrapper, text) {
    return wrapper.findAll("button").find((button) => button.text().includes(text));
  }

  it("loads repo stats through the API client, routes hero actions, and persists sort changes", async () => {
    const wrapper = mountPage();
    await flushPromises();

    expect(requests).toEqual([
      {
        type: "model",
        params: {
          limit: "100",
          sort: "trending",
          fallback: "false",
        },
      },
      {
        type: "dataset",
        params: {
          limit: "100",
          sort: "trending",
          fallback: "false",
        },
      },
      {
        type: "space",
        params: {
          limit: "100",
          sort: "trending",
          fallback: "false",
        },
      },
    ]);

    expect(wrapper.text()).toContain("中文开源AI模型社区");
    expect(wrapper.text()).toContain("社区精选");
    expect(wrapper.text()).toContain("mai_lin/lineart-caption-base");
    expect(wrapper.text()).toContain("mai_lin/street-sign-zh-en");
    expect(wrapper.text()).toContain("mai_lin/mai_lin");

    await findButtonByText(wrapper, "浏览开源模型").trigger("click");
    await findButtonByText(wrapper, "体验在线 Demo").trigger("click");
    await findButtonByText(wrapper, "查看全部模型").trigger("click");
    await findButtonByText(wrapper, "查看全部数据集").trigger("click");
    await findButtonByText(wrapper, "查看全部空间").trigger("click");

    await wrapper.get('select[data-el-select="true"]').setValue("likes");
    await flushPromises();
    expect(wrapper.text()).toContain("点赞热榜");

    await wrapper.get('select[data-el-select="true"]').setValue("recent");
    await flushPromises();
    expect(wrapper.text()).toContain("最新创建");

    await wrapper.get('select[data-el-select="true"]').setValue("updated");
    await flushPromises();
    expect(wrapper.text()).toContain("最近更新");

    await wrapper.get('select[data-el-select="true"]').setValue("downloads");
    await flushPromises();
    expect(wrapper.text()).toContain("下载热榜");

    expect(mocks.repoSortPreference.setRepoSortPreference).toHaveBeenCalledWith(
      {
        scope: "home",
        repoType: "all",
        value: "downloads",
      },
    );
    expect(mocks.router.push).toHaveBeenCalledWith("/get-started");
    expect(mocks.router.push).toHaveBeenCalledWith("/spaces");
    expect(mocks.router.push).toHaveBeenCalledWith("/models");
    expect(mocks.router.push).toHaveBeenCalledWith("/datasets");
    expect(mocks.router.push).toHaveBeenCalledWith("/spaces");
  });

  it("handles invalid token query params and cleans up the URL", async () => {
    mocks.route.query = {
      error: "invalid_token",
      message: encodeURIComponent("Invitation expired"),
    };

    const wrapper = mountPage();
    await flushPromises();

    expect(mocks.router.replace).toHaveBeenCalledWith("/");
    expect(wrapper.text()).toContain("中文开源AI模型社区");
  });

  it("handles missing users and renders fallback metrics", async () => {
    mocks.route.query = {
      error: "user_not_found",
    };
    installHandlers({
      modelRepos: [
        {
          ...cloneFixture(uiApiFixtures.repo.info),
          id: "mai_lin/model-demo",
          downloads: undefined,
          likes: undefined,
          lastModified: null,
        },
      ],
      datasetRepos: [
        {
          ...cloneFixture(uiApiFixtures.repo.info),
          id: "mai_lin/dataset-demo",
          downloads: undefined,
          likes: undefined,
          lastModified: null,
        },
      ],
      spaceRepos: [
        {
          ...cloneFixture(uiApiFixtures.repo.info),
          id: "mai_lin/space-demo",
          downloads: undefined,
          likes: undefined,
          lastModified: null,
        },
      ],
    });

    const wrapper = mountPage();
    await flushPromises();

    expect(mocks.router.replace).toHaveBeenCalledWith("/");
    expect(wrapper.text()).toContain("never");
    expect(wrapper.text()).toContain("0");
  });

  it("ignores unknown query errors and load failures without redirecting", async () => {
    mocks.route.query = {
      error: "something_else",
    };
    server.use(
      http.get("/api/models", () => jsonResponse({ detail: "boom" }, { status: 500 })),
    );

    const wrapper = mountPage();
    await flushPromises();

    expect(mocks.elMessage.error).not.toHaveBeenCalled();
    expect(mocks.router.replace).not.toHaveBeenCalled();
    expect(wrapper.text()).toContain("中文开源AI模型社区");
  });
});
