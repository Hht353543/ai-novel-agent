/**
 * localStorage 安全写入工具。
 *
 * 附件等大内容可能触发浏览器配额错误（QuotaExceededError），
 * 这里统一吞掉异常，保证不影响主流程（内容仍保存在内存，可手动保存项目）。
 */

export function safeSetItem(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    // 存储满 / 被禁用时静默忽略
  }
}

export function safeRemoveItem(key: string): void {
  try {
    localStorage.removeItem(key);
  } catch {
    // 忽略
  }
}

/** 未保存项目的本地标识键（与 novel_outline 配套，标识同一份大纲的草稿归属） */
export const OUTLINE_PROJECT_KEY = "novel_outline_project_key";

/** 大纲页最新大纲备份键 */
export const OUTLINE_KEY = "novel_outline";

/** 最近打开的项目 ID 键（章节写作页启动时优先恢复） */
export const LAST_PROJECT_KEY = "novel_last_project_id";

/** 大纲页表单备份键 */
export const FORM_KEY = "novel_form";

/** 大纲页附件备份键 */
export const FORM_ATTACH_KEY = "novel_form_attachment";

/** 生成一个稳定的本地项目标识（大纲尚未保存到后端时使用） */
export function generateProjectKey(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `local_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`;
}

/** 章节草稿键前缀（视图扫描本地键时复用同一前缀定义） */
export function chapterDraftPrefix(projectKey: string): string {
  return `novel_chapter_${projectKey}_`;
}

/** 章节草稿键：按项目标识隔离，避免同名项目共用数据 */
export function chapterDraftKey(
  projectKey: string,
  volumeIndex: number,
  chapterIndex: number,
): string {
  return `${chapterDraftPrefix(projectKey)}${volumeIndex}_${chapterIndex}`;
}

/** 章节额外要求键 */
export function chapterExtraKey(
  projectKey: string,
  volumeIndex: number,
  chapterIndex: number,
): string {
  return `novel_extra_${projectKey}_${volumeIndex}_${chapterIndex}`;
}

/** 章节附件键 */
export function chapterAttachKey(
  projectKey: string,
  volumeIndex: number,
  chapterIndex: number,
): string {
  return `novel_attach_${projectKey}_${volumeIndex}_${chapterIndex}`;
}

/** 角色卡备份键 */
export function chapterCardsKey(projectKey: string): string {
  return `novel_cards_${projectKey}`;
}

/** 把一个项目标识下的本地数据复制到另一个标识（目标已存在时不覆盖，源数据保留） */
export function copyProjectKeys(fromProjectKey: string, toProjectKey: string): void {
  copyPrefixedKeys(
    chapterDraftPrefix(fromProjectKey),
    (suffix) => chapterDraftPrefix(toProjectKey) + suffix,
  );
  copyPrefixedKeys(
    `novel_extra_${fromProjectKey}_`,
    (suffix) => `novel_extra_${toProjectKey}_${suffix}`,
  );
  copyPrefixedKeys(
    `novel_attach_${fromProjectKey}_`,
    (suffix) => `novel_attach_${toProjectKey}_${suffix}`,
  );
  copySingleKey(`novel_cards_${fromProjectKey}`, `novel_cards_${toProjectKey}`);
}

/**
 * 一次性只读迁移：把旧「书名」键前缀下的数据复制到新项目标识。
 * 只在目标键不存在时复制，不覆盖新数据、不删除旧键，避免升级丢数据。
 */
export function migrateLegacyProjectKeys(projectKey: string, title: string): void {
  const legacyTitle = title || "novel";
  copyPrefixedKeys(
    `novel_chapter_${legacyTitle}_`,
    (suffix) => `novel_chapter_${projectKey}_${suffix}`,
  );
  copyPrefixedKeys(
    `novel_extra_${legacyTitle}_`,
    (suffix) => `novel_extra_${projectKey}_${suffix}`,
  );
  copyPrefixedKeys(
    `novel_attach_${legacyTitle}_`,
    (suffix) => `novel_attach_${projectKey}_${suffix}`,
  );
  copySingleKey(`novel_cards_${legacyTitle}`, `novel_cards_${projectKey}`);
}

function copyPrefixedKeys(prefix: string, mapSuffix: (suffix: string) => string): void {
  const pending: Array<[string, string]> = [];
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (!key || !key.startsWith(prefix)) continue;
    const suffix = key.slice(prefix.length);
    if (!/^\d+_\d+$/.test(suffix)) continue;
    const target = mapSuffix(suffix);
    if (localStorage.getItem(target) !== null) continue;
    pending.push([key, target]);
  }
  for (const [source, target] of pending) {
    const value = localStorage.getItem(source);
    if (value !== null) safeSetItem(target, value);
  }
}

function copySingleKey(source: string, target: string): void {
  if (localStorage.getItem(target) !== null) return;
  const value = localStorage.getItem(source);
  if (value !== null) safeSetItem(target, value);
}
