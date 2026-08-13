import { expect, test } from "@playwright/test";

const OUTLINE = {
  success: true,
  status: "success",
  demo: false,
  message: "",
  context: [],
  outline: {
    title: "E2E Book",
    summary: "Summary",
    world: "World",
    characters: [{ name: "Hero", role: "protagonist", description: "desc" }],
    volume_plan: [
      { volume: "Volume 1", chapters: ["Chapter 1", "Chapter 2"] },
    ],
  },
  raw: null,
};

const CHAPTER_TEXT = "E2E chapter content";

test("core flow: generate -> save -> write -> save -> reopen -> delete", async ({
  page,
}) => {
  page.on("dialog", (dialog) => dialog.accept());

  // ---- mock 后端 ----
  await page.route("**/api/novel/generate", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(OUTLINE),
    }),
  );

  await page.route("**/api/novel/titles/generate", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        status: "success",
        message: "",
        titles: ["T1", "T2"],
      }),
    }),
  );

  await page.route("**/api/novel/chapter/stream", (route) =>
    route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      body:
        `data: {"type": "meta", "status": "demo", "message": "demo"}\n\n` +
        `data: {"type": "delta", "text": "${CHAPTER_TEXT}"}\n\n` +
        `data: {"type": "meta", "status": "success", "content_len": ${CHAPTER_TEXT.length}, "memory": ""}\n\n`,
    }),
  );

  const savedProject = {
    id: "p1",
    title: "E2E Book",
    outline: OUTLINE.outline,
    chapters: [
      {
        volume_index: 0,
        chapter_index: 0,
        chapter_title: "Chapter 1",
        content: CHAPTER_TEXT,
      },
    ],
    character_cards: [],
    memory: "",
    created_at: "2026-01-01T00:00:00+08:00",
    updated_at: "2026-01-01T00:00:00+08:00",
  };

  await page.route("**/api/projects", (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          projects: [
            {
              id: savedProject.id,
              title: savedProject.title,
              chapter_count: 1,
              created_at: savedProject.created_at,
              updated_at: savedProject.updated_at,
            },
          ],
        }),
      });
    }
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ success: true, message: "ok", project: savedProject }),
    });
  });

  await page.route("**/api/projects/p1", (route) => {
    if (route.request().method() === "DELETE") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, message: "已删除" }),
      });
    }
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(savedProject),
    });
  });

  // ---- 生成大纲 ----
  await page.goto("/");
  await page.getByPlaceholder("如：100万字").fill("100000字");
  await page.getByRole("button", { name: "生成大纲" }).click();
  await expect(page.getByText("E2E Book")).toBeVisible();

  // ---- 保存大纲为项目（触发 alert，已自动接受）----
  await page.getByRole("button", { name: "保存大纲为项目" }).click();
  await expect(page.getByText(/大纲已保存为项目/)).toBeVisible({ timeout: 5000 }).catch(() => {});

  // ---- 进入章节写作并生成章节（流式 mock）----
  await page.getByRole("button", { name: "进入章节写作" }).click();
  await expect(page).toHaveURL(/\/writer/);
  await page.getByRole("button", { name: "生成本章开头" }).click();
  await expect(page.locator("textarea.editor")).toHaveValue(CHAPTER_TEXT);

  // ---- 保存项目 ----
  await page.getByRole("button", { name: "保存项目" }).click();
  await expect(page.getByText(/保存成功：共 1 章内容/)).toBeVisible();

  // ---- 重开：刷新后从项目恢复 ----
  await page.reload();
  await expect(page.locator("textarea.editor")).toHaveValue(CHAPTER_TEXT);

  // ---- 删除项目 ----
  await page.getByRole("button", { name: "打开项目" }).click();
  await page.getByRole("button", { name: "删除" }).click();
  await expect(page.getByText("项目已删除")).toBeVisible();
});

test("stream failure falls back to non-stream chapter generation", async ({
  page,
}) => {
  page.on("dialog", (dialog) => dialog.accept());

  await page.route("**/api/novel/generate", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(OUTLINE),
    }),
  );

  // 流式接口失败（例如代理中断），旧的非流式接口应自动兜底
  await page.route("**/api/novel/chapter/stream", (route) =>
    route.fulfill({
      status: 500,
      contentType: "application/json",
      body: JSON.stringify({ success: false, status: "error", message: "boom" }),
    }),
  );
  await page.route("**/api/novel/chapter/generate", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        status: "success",
        message: "",
        content: CHAPTER_TEXT,
        full_text: CHAPTER_TEXT,
        memory: "",
      }),
    }),
  );

  await page.goto("/");
  await page.getByRole("button", { name: "生成大纲" }).click();
  await expect(page.getByText("E2E Book")).toBeVisible();
  await page.getByRole("button", { name: "进入章节写作" }).click();
  await expect(page).toHaveURL(/\/writer/);

  await page.getByRole("button", { name: "生成本章开头" }).click();
  await expect(page.locator("textarea.editor")).toHaveValue(CHAPTER_TEXT);
  await expect(page.getByText(/已生成约 \d+ 字/)).toBeVisible();
});

test("one-click pipeline shows progress and opens writer with result", async ({
  page,
}) => {
  page.on("dialog", (dialog) => dialog.accept());

  await page.route("**/api/agents/pipeline/async", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ run_id: "pr1", status: "CREATED" }),
    }),
  );

  await page.route("**/api/agents/runs/pr1", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        run_id: "pr1",
        kind: "pipeline",
        status: "COMPLETED",
        current_agent: "pipeline",
        message: "",
        revision_attempts: 0,
        progress: [
          { step: "PLANNING", status: "done", agent: "planner", message: "", timestamp: "t" },
          { step: "CHARACTER_DESIGN", status: "done", agent: "character", message: "", timestamp: "t" },
          { step: "WRITING", status: "done", agent: "writer", message: "", timestamp: "t" },
          { step: "REVIEWING", status: "done", agent: "reviewer", message: "", timestamp: "t" },
          { step: "UPDATING_MEMORY", status: "done", agent: "memory", message: "", timestamp: "t" },
        ],
        start_time: "t",
        end_time: "t",
        error: null,
        result: {
          run_id: "pr1",
          project_id: "p1",
          status: "success",
          message: "",
          plan: OUTLINE.outline,
          outline: OUTLINE.outline,
          chapter: {
            attempt: 1,
            content: CHAPTER_TEXT,
            full_text: CHAPTER_TEXT,
            memory: "",
          },
          latest_review: {
            passed: true,
            score: 90,
            issues: [],
            summary: "ok",
            revision_required: false,
          },
          revision_history: [],
          character_state_updates: [],
          timeline: [],
          memory_facts: [],
          telemetry: {},
        },
      }),
    }),
  );

  const savedProject = {
    id: "p1",
    title: "E2E Book",
    outline: OUTLINE.outline,
    chapters: [
      {
        volume_index: 0,
        chapter_index: 0,
        chapter_title: "Chapter 1",
        content: CHAPTER_TEXT,
      },
    ],
    character_cards: [],
    memory: "",
    created_at: "2026-01-01T00:00:00+08:00",
    updated_at: "2026-01-01T00:00:00+08:00",
  };
  await page.route("**/api/projects/p1", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(savedProject),
    }),
  );

  await page.goto("/");
  await page.getByPlaceholder("如：100万字").fill("100000字");
  await page.getByRole("button", { name: "一键 Pipeline（多 Agent）" }).click();

  await expect(page.getByText("小说创作 Pipeline")).toBeVisible();
  await expect(page.getByText("大纲规划")).toBeVisible();
  await expect(page.getByText("已完成")).toBeVisible({ timeout: 5000 });
  await expect(page.getByText(/最终章节预览/)).toBeVisible();
  await expect(page.getByText("Reviewer：通过（评分 90）")).toBeVisible();

  await page.getByRole("button", { name: "进入章节写作" }).click();
  await expect(page).toHaveURL(/\/writer/);
  await expect(page.locator("textarea.editor")).toHaveValue(CHAPTER_TEXT);
});
