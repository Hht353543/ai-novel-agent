import { beforeEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";

vi.mock("vue-router", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("../../api/novel", () => ({
  generateNovel: vi.fn(),
  generateTitles: vi.fn(),
}));

vi.mock("../../api/project", () => ({
  saveProject: vi.fn(),
}));

import { generateNovel } from "../../api/novel";
import NovelGeneratorView from "../NovelGeneratorView.vue";

function makeResult(status: "success" | "demo" | "error") {
  return {
    success: status !== "error",
    status,
    demo: status === "demo",
    message: "",
    context: [],
    outline: { title: "T", summary: "S", world: "W", characters: [], volume_plan: [] },
    raw: null,
  };
}

describe("NovelGeneratorView", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it("enables save for demo results", async () => {
    vi.mocked(generateNovel).mockResolvedValue(makeResult("demo"));
    const wrapper = mount(NovelGeneratorView);
    await wrapper.find(".generate-btn").trigger("click");
    await flushPromises();
    const btn = wrapper.find(".save-btn");
    expect(btn.attributes("disabled")).toBeUndefined();
  });

  it("disables save for error results", async () => {
    vi.mocked(generateNovel).mockResolvedValue(makeResult("error"));
    const wrapper = mount(NovelGeneratorView);
    await wrapper.find(".generate-btn").trigger("click");
    await flushPromises();
    const btn = wrapper.find(".save-btn");
    expect(btn.attributes("disabled")).toBeDefined();
  });
});
