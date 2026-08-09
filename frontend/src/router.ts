/**
 * 路由配置（当前仅一个页面，预留后续扩展）。
 */
import { createRouter, createWebHistory } from "vue-router";
import NovelGeneratorView from "./views/NovelGeneratorView.vue";
import ChapterWriterView from "./views/ChapterWriterView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "home",
      component: NovelGeneratorView,
    },
    {
      path: "/writer",
      name: "writer",
      component: ChapterWriterView,
    },
  ],
});

export default router;
