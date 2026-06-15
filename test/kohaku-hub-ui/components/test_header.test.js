import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { nextTick } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ElementPlusStubs, RouterLinkStub } from "../helpers/vue";
import { flushPromises } from "@vue/test-utils";

const mocks = vi.hoisted(() => ({
  router: {
    push: vi.fn(),
  },
  route: {
    params: {},
    query: {},
  },
  elMessage: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock("vue-router/auto", () => ({
  useRouter: () => mocks.router,
  useRoute: () => mocks.route,
}));

vi.mock("element-plus", () => ({
  ElMessage: mocks.elMessage,
}));

import TheHeader from "@/components/layout/TheHeader.vue";
import { useAuthStore } from "@/stores/auth";
import { useThemeStore } from "@/stores/theme";

describe("TheHeader", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    document.documentElement.className = "";
    setActivePinia(createPinia());
  });

  function mountHeader() {
    return mount(TheHeader, {
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

  it("renders visitor navigation and toggles theme", async () => {
    const themeStore = useThemeStore();
    const wrapper = mountHeader();

    expect(wrapper.text()).toContain("模型");
    expect(wrapper.text()).toContain("数据集");
    expect(wrapper.text()).toContain("登录");
    expect(wrapper.text()).toContain("注册");

    const buttons = wrapper.findAll("button");
    await buttons[0].trigger("click");

    expect(themeStore.isDark).toBe(true);
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    expect(localStorage.getItem("theme")).toBe("dark");

    await findButtonByText(wrapper, "注册").trigger("click");
    expect(mocks.router.push).toHaveBeenCalledWith("/register");
  });

  it("renders authenticated actions and routes create/profile/logout flows", async () => {
    const authStore = useAuthStore();
    authStore.user = {
      username: "alice",
    };
    authStore.logout = vi.fn().mockResolvedValue(undefined);

    const wrapper = mountHeader();

    expect(wrapper.text()).toContain("alice");
    expect(wrapper.text()).toContain("新建模型");
    expect(wrapper.text()).toContain("新建数据集");
    expect(wrapper.text()).toContain("新建空间");
    expect(wrapper.text()).toContain("个人主页");
    expect(wrapper.text()).toContain("个人设置");
    expect(wrapper.text()).toContain("退出登录");

    await findButtonByText(wrapper, "新建模型").trigger("click");
    await findButtonByText(wrapper, "个人主页").trigger("click");
    await findButtonByText(wrapper, "个人设置").trigger("click");
    await findButtonByText(wrapper, "退出登录").trigger("click");

    expect(mocks.router.push).toHaveBeenCalledWith({
      path: "/new",
      query: { type: "model" },
    });
    expect(mocks.router.push).toHaveBeenCalledWith("/alice");
    expect(mocks.router.push).toHaveBeenCalledWith("/settings");
    expect(authStore.logout).toHaveBeenCalled();
    expect(mocks.router.push).toHaveBeenCalledWith("/");
  });

  it("opens the mobile menu and falls back to the default avatar", async () => {
    const authStore = useAuthStore();
    authStore.user = {
      username: "alice",
    };
    authStore.logout = vi.fn().mockResolvedValue(undefined);

    const wrapper = mountHeader();

    const menuButton = wrapper
      .findAll("button")
      .find((button) => button.find(".i-carbon-menu").exists());
    await menuButton.trigger("click");
    await nextTick();

    expect(wrapper.find('[data-el-drawer="true"]').exists()).toBe(true);

    const avatar = wrapper.get('img[alt="alice avatar"]');
    await avatar.trigger("error");
    await nextTick();

    expect(wrapper.find(".i-carbon-user-avatar").exists()).toBe(true);
  });

  it("shows an error message when logout fails", async () => {
    const authStore = useAuthStore();
    authStore.user = {
      username: "alice",
    };
    authStore.logout = vi.fn().mockRejectedValue(new Error("network"));

    const wrapper = mountHeader();

    await findButtonByText(wrapper, "退出登录").trigger("click");
    await flushPromises();

    expect(authStore.logout).toHaveBeenCalled();
    expect(mocks.router.push).not.toHaveBeenCalledWith("/");
  });
});
