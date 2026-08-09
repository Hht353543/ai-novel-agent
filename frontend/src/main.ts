/**
 * 前端应用入口：创建 Vue 应用并挂载到 #app。
 */
import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";

createApp(App).use(router).mount("#app");
