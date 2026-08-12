import { describe, expect, it } from "vitest";
import {
  buildChapterPayload,
  joinStream,
  modeName,
} from "../useWriterActions";

const OUTLINE = {
  title: "T",
  summary: "S",
  world: "W",
  characters: [],
  volume_plan: [{ volume: "第一卷", chapters: ["第1章"] }],
};

describe("useWriterActions pure helpers", () => {
  it("modeName maps generation modes to Chinese labels", () => {
    expect(modeName("generate")).toBe("章节开头");
    expect(modeName("continue")).toBe("从文末续写");
    expect(modeName("rewrite")).toBe("从光标处重写");
    expect(modeName("unknown")).toBe("章节开头");
  });

  it("joinStream keeps base text unchanged when empty", () => {
    expect(joinStream("", "正文")).toBe("正文");
  });

  it("joinStream appends streamed text with a blank line", () => {
    expect(joinStream("上文  ", "续写")).toBe("上文\n\n续写");
  });

  it("buildChapterPayload maps camelCase state to snake_case API payload", () => {
    const payload = buildChapterPayload({
      outline: OUTLINE,
      volumeIndex: 0,
      chapterIndex: 0,
      chapterTitle: "第1章",
      contextText: "上文",
      previousChapterText: "前章",
      mode: "continue",
      targetLength: 800,
      characterCards: [],
      extraRequirements: " 风格明快 ",
      attachmentName: "a.txt",
      attachmentText: "附件内容",
      memory: "记忆",
    });
    expect(payload).toEqual({
      outline: OUTLINE,
      volume_index: 0,
      chapter_index: 0,
      chapter_title: "第1章",
      context_text: "上文",
      previous_chapter_text: "前章",
      mode: "continue",
      target_length: 800,
      character_cards: [],
      extra_requirements: "风格明快",
      attachment_name: "a.txt",
      attachment_text: "附件内容",
      memory: "记忆",
    });
  });
});
