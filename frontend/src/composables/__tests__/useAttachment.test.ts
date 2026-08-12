import { beforeEach, describe, expect, it } from "vitest";
import { useAttachment } from "../useAttachment";

function makeFile(name: string, content: string) {
  return { name, content } as unknown as File;
}

function stubFileReader() {
  (globalThis as Record<string, unknown>).FileReader = class {
    result = "";
    onload: (() => void) | null = null;
    onerror: (() => void) | null = null;
    readAsText(file: { content: string }) {
      this.result = file.content;
      if (this.onload) this.onload();
    }
  };
}

describe("useAttachment", () => {
  beforeEach(() => {
    localStorage.clear();
    stubFileReader();
  });

  it("restores valid attachment from storage", () => {
    localStorage.setItem("att", JSON.stringify({ name: "a.txt", content: "x" }));
    const att = useAttachment(() => "att");
    att.restore();
    expect(att.attachment.value?.name).toBe("a.txt");
    expect(att.attachment.value?.content).toBe("x");
  });

  it("ignores invalid stored attachment", () => {
    localStorage.setItem("att", JSON.stringify({ name: 123 }));
    const att = useAttachment(() => "att");
    att.restore();
    expect(att.attachment.value).toBeNull();
  });

  it("stores uploaded txt and notifies success", () => {
    const errors: string[] = [];
    const att = useAttachment(() => "att", (msg) => errors.push(msg));
    att.onAttachFile({
      target: { files: [makeFile("book.txt", "content")], value: "" },
    } as unknown as Event);
    expect(att.attachment.value?.name).toBe("book.txt");
    expect(JSON.parse(localStorage.getItem("att") ?? "{}").content).toBe("content");
    expect(errors).toEqual([""]);
  });

  it("rejects non-txt files", () => {
    const errors: string[] = [];
    const att = useAttachment(() => "att", (msg) => errors.push(msg));
    att.onAttachFile({
      target: { files: [makeFile("book.pdf", "x")], value: "" },
    } as unknown as Event);
    expect(errors[0]).toBe("请选择 .txt 文本文件");
  });

  it("removes attachment and storage", () => {
    localStorage.setItem("att", JSON.stringify({ name: "a.txt", content: "x" }));
    const att = useAttachment(() => "att");
    att.restore();
    att.removeAttachment();
    expect(att.attachment.value).toBeNull();
    expect(localStorage.getItem("att")).toBeNull();
  });
});
