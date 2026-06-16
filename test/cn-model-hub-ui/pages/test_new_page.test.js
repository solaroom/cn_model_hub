import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "@/testing/msw";
import { ElementPlusStubs, InvalidElFormStub } from "../helpers/vue";
import {
  cloneFixture,
  jsonResponse,
  readJsonBody,
  uiApiFixtures,
} from "../helpers/api-fixtures";
import { server } from "../setup/msw-server";
import { createMemoryHistory, createRouter } from "@/testing/router";

const mocks = vi.hoisted(() => ({
  elMessage: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
  },
}));

vi.mock("element-plus", () => ({
  ElMessage: mocks.elMessage,
}));

import { useAuthStore } from "@/stores/auth";
import NewRepoPage from "@/pages/new.vue";

describe("new repository page", () => {
  const createRequests = [];

  function installHandlers({
    createStatus = 200,
    createResponse = cloneFixture(uiApiFixtures.repo.create),
  } = {}) {
    createRequests.length = 0;

    server.use(
      http.post("/api/repos/create", async ({ request }) => {
        createRequests.push(await readJsonBody(request));
        return jsonResponse(createResponse, { status: createStatus });
      }),
    );
  }

  beforeEach(() => {
    vi.clearAllMocks();
    setActivePinia(createPinia());
    installHandlers();
  });

  async function createTestRouter(initialPath) {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: "/new", component: { template: "<div />" } },
        { path: "/:pathMatch(.*)*", component: { template: "<div />" } },
      ],
    });

    await router.push(initialPath);
    await router.isReady();
    return router;
  }

  function mountPage(router, extraStubs = {}) {
    return mount(NewRepoPage, {
      global: {
        plugins: [router],
        stubs: {
          ...ElementPlusStubs,
          ...extraStubs,
        },
      },
    });
  }

  function findButtonByText(wrapper, text) {
    return wrapper.findAll("button").find((button) => button.text().includes(text));
  }

  it("creates repositories for organizations through the API client and navigates to the new repo", async () => {
    const router = await createTestRouter("/new?type=dataset");
    const pushSpy = vi.spyOn(router, "push");
    const authStore = useAuthStore();
    authStore.user = { username: "mai_lin" };
    authStore.userOrganizations = [{ name: "aurora-labs" }];

    const wrapper = mountPage(router);
    await wrapper.find('select[data-el-select="true"]').setValue("aurora-labs");
    await wrapper.find('input[placeholder="my-awesome-dataset"]').setValue("vision-set");
    await findButtonByText(wrapper, "创建数据集").trigger("click");
    await flushPromises();

    expect(createRequests).toEqual([
      {
        type: "dataset",
        name: "vision-set",
        organization: "aurora-labs",
        private: false,
      },
    ]);
    expect(pushSpy).toHaveBeenCalledWith("/datasets/acme/fresh-model");
  });

  it("keeps the personal namespace null and stays on the page after failures", async () => {
    installHandlers({
      createStatus: 400,
      createResponse: {
        detail: "Name already exists",
      },
    });

    const router = await createTestRouter("/new?type=space");
    const pushSpy = vi.spyOn(router, "push");
    const authStore = useAuthStore();
    authStore.user = { username: "mai_lin" };
    authStore.userOrganizations = [];

    const wrapper = mountPage(router);
    await wrapper.find('input[placeholder="my-awesome-space"]').setValue("my-demo");
    await findButtonByText(wrapper, "创建空间").trigger("click");
    await flushPromises();

    expect(createRequests).toEqual([
      {
        type: "space",
        name: "my-demo",
        organization: null,
        private: false,
      },
    ]);
    expect(pushSpy).not.toHaveBeenCalled();
  });

  it("falls back to the current username when the backend omits repo_id", async () => {
    installHandlers({
      createResponse: cloneFixture(uiApiFixtures.repo.createWithoutId),
    });

    const router = await createTestRouter("/new");
    const pushSpy = vi.spyOn(router, "push");
    const authStore = useAuthStore();
    authStore.user = { username: "mai_lin" };
    authStore.userOrganizations = [];

    const wrapper = mountPage(router);
    await wrapper.find('input[placeholder="my-awesome-model"]').setValue("fresh-model");
    await findButtonByText(wrapper, "创建模型").trigger("click");
    await flushPromises();

    expect(createRequests).toEqual([
      {
        type: "model",
        name: "fresh-model",
        organization: null,
        private: false,
      },
    ]);
    expect(pushSpy).toHaveBeenCalledWith("/models/mai_lin/fresh-model");
  });

  it("ignores invalid type query values and accepts later valid updates", async () => {
    const router = await createTestRouter("/new?type=unknown");
    const wrapper = mountPage(router);
    await flushPromises();

    expect(wrapper.text()).toContain("新建仓库");
    expect(wrapper.text()).toContain("仓库用于存放项目文件");

    await router.push("/new?type=space");
    await flushPromises();

    expect(wrapper.text()).toContain("创建空间");
  });

  it("surfaces the backend 409 conflict message when the repo already exists", async () => {
    installHandlers({
      createStatus: 409,
      createResponse: {
        url: "http://testserver/models/mai_lin/fresh-model",
        repo_id: "mai_lin/fresh-model",
        error: "Repository mai_lin/fresh-model already exists",
      },
    });

    const router = await createTestRouter("/new");
    const pushSpy = vi.spyOn(router, "push");
    const authStore = useAuthStore();
    authStore.user = { username: "mai_lin" };
    authStore.userOrganizations = [];

    const wrapper = mountPage(router);
    await wrapper.find('input[placeholder="my-awesome-model"]').setValue("fresh-model");
    await findButtonByText(wrapper, "创建模型").trigger("click");
    await flushPromises();

    expect(mocks.elMessage.error).toHaveBeenCalledWith(
      "Repository mai_lin/fresh-model already exists",
    );
    expect(pushSpy).not.toHaveBeenCalled();
  });

  it("falls back to legacy detail-shaped error bodies", async () => {
    installHandlers({
      createStatus: 400,
      createResponse: {
        detail: "Invalid repository name",
      },
    });

    const router = await createTestRouter("/new");
    const authStore = useAuthStore();
    authStore.user = { username: "mai_lin" };
    authStore.userOrganizations = [];

    const wrapper = mountPage(router);
    await wrapper.find('input[placeholder="my-awesome-model"]').setValue("bad-name");
    await findButtonByText(wrapper, "创建模型").trigger("click");
    await flushPromises();

    expect(mocks.elMessage.error).toHaveBeenCalledWith("Invalid repository name");
  });

  it("stops invalid submissions and handles fallback create errors", async () => {
    installHandlers({
      createStatus: 500,
      createResponse: {
        detail: "boom",
      },
    });

    const router = await createTestRouter("/new");
    const authStore = useAuthStore();
    authStore.user = { username: "mai_lin" };
    authStore.userOrganizations = [];

    const invalidWrapper = mountPage(router, {
      ElForm: InvalidElFormStub,
    });
    await flushPromises();
    await findButtonByText(invalidWrapper, "创建模型").trigger("click");
    await flushPromises();
    expect(createRequests).toEqual([]);

    const wrapper = mountPage(router);
    await wrapper.find('input[placeholder="my-awesome-model"]').setValue("fresh-model");
    await findButtonByText(wrapper, "创建模型").trigger("click");
    await flushPromises();

    expect(createRequests).toEqual([
      {
        type: "model",
        name: "fresh-model",
        organization: null,
        private: false,
      },
    ]);
  });
});
