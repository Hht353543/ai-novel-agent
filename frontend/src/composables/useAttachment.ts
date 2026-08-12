import { ref } from "vue";

export interface Attachment {
  name: string;
  content: string;
}

/**
 * 本地 txt 附件：读取、校验、存储与移除。
 * storageKey 为函数，便于写作页按「项目标识 + 章节」动态取键。
 */
export function useAttachment(
  storageKey: () => string,
  onError?: (message: string) => void,
) {
  const attachment = ref<Attachment | null>(null);

  function restore(): void {
    try {
      const raw = localStorage.getItem(storageKey());
      if (raw) {
        const saved = JSON.parse(raw) as unknown;
        if (
          saved &&
          typeof saved === "object" &&
          typeof (saved as Attachment).name === "string" &&
          typeof (saved as Attachment).content === "string"
        ) {
          attachment.value = saved as Attachment;
          return;
        }
      }
      attachment.value = null;
    } catch {
      attachment.value = null;
    }
  }

  function onAttachFile(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".txt")) {
      onError?.("请选择 .txt 文本文件");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      attachment.value = {
        name: file.name,
        content: String(reader.result ?? ""),
      };
      try {
        localStorage.setItem(storageKey(), JSON.stringify(attachment.value));
      } catch {
        // 存储满 / 被禁用时静默忽略
      }
      onError?.("");
    };
    reader.onerror = () => {
      onError?.("读取附件失败，请重试");
    };
    reader.readAsText(file, "utf-8");
    input.value = "";
  }

  function removeAttachment(): void {
    attachment.value = null;
    try {
      localStorage.removeItem(storageKey());
    } catch {
      // 忽略
    }
  }

  return { attachment, restore, onAttachFile, removeAttachment };
}
