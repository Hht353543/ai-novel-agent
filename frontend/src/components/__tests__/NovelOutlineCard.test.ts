import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import NovelOutlineCard from "../NovelOutlineCard.vue";
import type { NovelOutline } from "../../api/novel";

const outline: NovelOutline = {
  title: "T",
  summary: "S",
  world: "W",
  characters: [{ name: "A", role: "hero", description: "d" }],
  volume_plan: [{ volume: "V1", chapters: ["c1", "c2"] }],
};

describe("NovelOutlineCard", () => {
  it("renders outline and emits generate-titles", async () => {
    const wrapper = mount(NovelOutlineCard, {
      props: { outline, generatingVolumeIndex: null },
    });
    expect(wrapper.text()).toContain("T");
    expect(wrapper.text()).toContain("V1");
    await wrapper.find(".title-btn").trigger("click");
    expect(wrapper.emitted("generate-titles")).toEqual([[0]]);
  });
});
