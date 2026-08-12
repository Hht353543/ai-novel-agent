import { beforeEach, describe, expect, it, vi } from "vitest";
import { useDraftStorage } from "../useDraftStorage";

describe("useDraftStorage", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.useRealTimers();
  });

  it("isolates drafts by project key", () => {
    const a = useDraftStorage();
    a.setProjectKey("P1");
    a.saveDraft(0, 0, "t", "draft-a");

    const b = useDraftStorage();
    b.setProjectKey("P2");
    expect(b.readDraft(0, 0)).toBe("");
    expect(a.readDraft(0, 0)).toBe("draft-a");
  });

  it("debounces draft writes to the last content", () => {
    vi.useFakeTimers();
    const s = useDraftStorage();
    s.setProjectKey("P");
    s.saveDraftDebounced(0, 0, "t", "a");
    s.saveDraftDebounced(0, 0, "t", "b");
    s.saveDraftDebounced(0, 0, "t", "c");
    expect(localStorage.getItem("novel_chapter_P_0_0")).toBeNull();
    vi.advanceTimersByTime(500);
    expect(localStorage.getItem("novel_chapter_P_0_0")).toBe("c");
    expect(s.getChapterDraft(0, 0)?.content).toBe("c");
  });

  it("flushDraft writes pending draft immediately", () => {
    vi.useFakeTimers();
    const s = useDraftStorage();
    s.setProjectKey("P");
    s.saveDraftDebounced(0, 1, "t", "x");
    s.flushDraft();
    expect(localStorage.getItem("novel_chapter_P_0_1")).toBe("x");
    vi.advanceTimersByTime(600);
    expect(localStorage.getItem("novel_chapter_P_0_1")).toBe("x");
  });

  it("migrates legacy keys without overwriting new ones", () => {
    localStorage.setItem("novel_chapter_Book_0_0", "legacy");
    localStorage.setItem("novel_chapter_P_0_0", "new");
    const s = useDraftStorage();
    s.setProjectKey("P");
    s.migrateLegacy("Book");
    expect(localStorage.getItem("novel_chapter_P_0_0")).toBe("new");
    localStorage.removeItem("novel_chapter_P_0_0");
    s.migrateLegacy("Book");
    expect(localStorage.getItem("novel_chapter_P_0_0")).toBe("legacy");
  });

  it("promoteToProject copies drafts and switches key", () => {
    const s = useDraftStorage();
    s.setProjectKey("LOCAL");
    s.saveDraft(1, 2, "t", "content");
    s.promoteToProject("SERVER");
    expect(s.projectKey.value).toBe("SERVER");
    expect(localStorage.getItem("novel_chapter_SERVER_1_2")).toBe("content");
    expect(localStorage.getItem("novel_chapter_LOCAL_1_2")).toBe("content");
  });
});
