import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "@/testing/msw";
import { server } from "../setup/msw-server";
import { ElementPlusStubs } from "../helpers/vue";

const mocks = vi.hoisted(() => ({
  elMessage: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock("element-plus", async () => {
  const actual = await vi.importActual("element-plus");
  return {
    ...actual,
    ElMessage: mocks.elMessage,
  };
});

import RepoMlflowPanel from "@/components/repo/RepoMlflowPanel.vue";

describe("RepoMlflowPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  function mountPanel(props = {}) {
    return mount(RepoMlflowPanel, {
      props: {
        repoType: "model",
        namespace: "owner",
        name: "demo-model",
        isOwner: true,
        initialBinding: {
          enabled: false,
          experiment_name: null,
          experiment_id: null,
          last_synced_at: null,
        },
        ...props,
      },
      global: {
        stubs: ElementPlusStubs,
      },
    });
  }

  it("loads binding and renders recent runs", async () => {
    server.use(
      http.get("/api/models/owner/demo-model/mlflow", () =>
        Response.json({
          enabled: true,
          experiment_name: "repo:model:owner/demo-model",
          experiment_id: "exp-777",
          last_synced_at: "2026-06-15T12:00:00+00:00",
        }),
      ),
      http.get("/api/models/owner/demo-model/mlflow/runs", () =>
        Response.json({
          enabled: true,
          experiment_name: "repo:model:owner/demo-model",
          experiment_id: "exp-777",
          runs: [
            {
              run_id: "run-1",
              run_name: "eval-main",
              status: "FINISHED",
              start_time: 1710000000000,
              metrics: { accuracy: 0.98 },
            },
          ],
        }),
      ),
    );

    const wrapper = mountPanel();
    await flushPromises();
    await flushPromises();

    expect(wrapper.text()).toContain("repo:model:owner/demo-model");
    expect(wrapper.text()).toContain("eval-main");
    expect(wrapper.text()).toContain("accuracy: 0.98");
  });

  it("binds an experiment and refreshes the state", async () => {
    let bound = false;
    server.use(
      http.get("/api/models/owner/demo-model/mlflow", () =>
        Response.json(
          bound
            ? {
                enabled: true,
                experiment_name: "repo:model:owner/demo-model",
                experiment_id: "exp-123",
                last_synced_at: "2026-06-15T12:00:00+00:00",
              }
            : {
                enabled: false,
                experiment_name: null,
                experiment_id: null,
                last_synced_at: null,
              },
        ),
      ),
      http.get("/api/models/owner/demo-model/mlflow/runs", () =>
        Response.json({
          enabled: bound,
          experiment_name: bound ? "repo:model:owner/demo-model" : null,
          experiment_id: bound ? "exp-123" : null,
          runs: [],
        }),
      ),
      http.post("/api/models/owner/demo-model/mlflow/bind", async () => {
        bound = true;
        return Response.json({
          success: true,
          mlflow: {
            enabled: true,
            experiment_name: "repo:model:owner/demo-model",
            experiment_id: "exp-123",
            last_synced_at: "2026-06-15T12:00:00+00:00",
          },
        });
      }),
    );

    const wrapper = mountPanel();
    await flushPromises();
    await flushPromises();

    const bindButton = wrapper
      .findAll("button")
      .find((button) => button.text().includes("Bind Experiment"));
    expect(bindButton).toBeTruthy();

    await bindButton.trigger("click");
    await flushPromises();
    await flushPromises();

    expect(mocks.elMessage.success).toHaveBeenCalled();
    expect(wrapper.text()).toContain("repo:model:owner/demo-model");
  });
});
