import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import ChapterEditor from "../ChapterEditor.vue";

describe("ChapterEditor", () => {
  const baseProps = {
    currentChapterTitle: "第1章",
    text: "正文内容",
    targetLength: 800,
    extraReq: "",
    chapterAttachment: null,
    loading: false,
    generatingTitle: false,
    reviewing: false,
    reviewIssues: [],
  };

  it("emits text updates and review", async () => {
    const wrapper = mount(ChapterEditor, { props: baseProps });
    const textarea = wrapper.find("textarea");
    await textarea.setValue("新正文");
    expect(wrapper.emitted("update:text")).toEqual([["新正文"]]);
    await wrapper.find("button.btn").trigger("click");
    expect(wrapper.emitted("generate")).toBeTruthy();
    const buttons = wrapper.findAll("button.btn");
    const reviewBtn = buttons.find((b) => b.text().includes("审校"));
    await reviewBtn?.trigger("click");
    expect(wrapper.emitted("review")).toBeTruthy();
  });

  it("renders review issues", () => {
    const wrapper = mount(ChapterEditor, {
      props: {
        ...baseProps,
        reviewIssues: [
          { type: "错字", severity: "high", description: "d", suggestion: "s" },
        ],
      },
    });
    expect(wrapper.text()).toContain("审校结果");
    expect(wrapper.text()).toContain("错字");
    expect(wrapper.text()).toContain("s");
  });
});
