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
