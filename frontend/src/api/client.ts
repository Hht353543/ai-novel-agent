/**
 * 后端请求统一封装：JSON 序列化、超时、错误归一。
 */

export const BASE_URL = "/api";

const DEFAULT_TIMEOUT_MS = 120_000;

/** 后端请求失败（非 2xx 或超时） */
export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export interface RequestOptions {
  method?: "GET" | "POST" | "DELETE";
  body?: unknown;
  /** 超时毫秒数，默认 120 秒 */
  timeoutMs?: number;
  /** 错误文案前缀（保持各接口原有提示） */
  errorLabel?: string;
  /** 是否把响应体文本拼进错误信息（默认 true） */
  includeErrorText?: boolean;
}

function isAbortError(err: unknown): boolean {
  return (
    typeof err === "object" &&
    err !== null &&
    "name" in err &&
    (err as { name?: unknown }).name === "AbortError"
  );
}

export async function request<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const {
    method = "GET",
    body,
    timeoutMs = DEFAULT_TIMEOUT_MS,
    errorLabel = "后端请求失败",
    includeErrorText = true,
  } = options;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${BASE_URL}${path}`, {
      method,
      headers:
        body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    });

    if (!response.ok) {
      const text = includeErrorText ? await response.text().catch(() => "") : "";
      const suffix = text ? `: ${text.slice(0, 200)}` : "";
      throw new ApiError(response.status, `${errorLabel} (${response.status})${suffix}`);
    }
    return (await response.json()) as T;
  } catch (err) {
    if (isAbortError(err)) {
      throw new ApiError(
        0,
        `${errorLabel}：请求超时（${Math.round(timeoutMs / 1000)} 秒），请检查后端服务后重试`,
      );
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}
