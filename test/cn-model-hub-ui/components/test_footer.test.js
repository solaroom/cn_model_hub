import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import TheFooter from "@/components/layout/TheFooter.vue";

describe("TheFooter", () => {
  it("renders the compact footer branding", () => {
    const wrapper = mount(TheFooter);
    const hrefs = wrapper.findAll("a").map((link) => link.attributes("href"));

    expect(wrapper.text()).toContain("cn_model_hub");
    expect(hrefs).toEqual([]);
  });
});
