<template>
  <div class="app-shell">
    <div class="app-bg" aria-hidden="true"></div>
    <header class="app-header">
      <router-link to="/" class="app-brand">
        <span class="brand-mark" aria-hidden="true"></span>
        <span class="brand-name">AI 网文作者 Agent</span>
      </router-link>
      <nav class="app-nav">
        <router-link to="/">大纲生成</router-link>
        <router-link to="/writer">章节写作</router-link>
      </nav>
    </header>
    <main class="app-main">
      <router-view />
    </main>
  </div>
</template>

<style>
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

:root {
  --bg: #f6f2ea;
  --panel: rgba(255, 253, 248, 0.86);
  --panel-solid: #fffdf8;
  --border: rgba(93, 82, 60, 0.14);
  --border-strong: rgba(93, 82, 60, 0.24);
  --text: #3a372f;
  --text-secondary: #6f6a5e;
  --text-muted: #9b948a;
  --accent: #c05621;
  --accent-2: #d97742;
  --success: #16a34a;
  --warning: #b45309;
  --danger: #dc2626;
  --radius: 16px;
  --radius-sm: 10px;
  --shadow: 0 16px 40px rgba(90, 80, 60, 0.12);
  --shadow-glow: 0 8px 28px rgba(192, 86, 33, 0.18);
}

body {
  font-family: "Inter", "PingFang SC", "Microsoft YaHei", "Helvetica Neue", Arial,
    sans-serif;
  background:
    radial-gradient(1100px 520px at 12% -8%, rgba(255, 196, 120, 0.3), transparent 62%),
    radial-gradient(900px 480px at 92% -4%, rgba(139, 92, 246, 0.1), transparent 58%),
    radial-gradient(700px 420px at 50% 110%, rgba(192, 86, 33, 0.07), transparent 60%),
    var(--bg);
  background-attachment: fixed;
  color: var(--text);
  min-height: 100vh;
  -webkit-font-smoothing: antialiased;
  line-height: 1.6;
}

::selection {
  background: rgba(192, 86, 33, 0.2);
}

::-webkit-scrollbar {
  width: 10px;
  height: 10px;
}

::-webkit-scrollbar-thumb {
  background: rgba(90, 80, 60, 0.16);
  border-radius: 999px;
  border: 2px solid transparent;
  background-clip: content-box;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(90, 80, 60, 0.28);
  background-clip: content-box;
}

.app-shell {
  position: relative;
  max-width: 1120px;
  margin: 0 auto;
  padding: 20px 24px 72px;
}

.app-bg {
  position: fixed;
  inset: 0;
  z-index: -1;
  pointer-events: none;
  background-image:
    linear-gradient(rgba(90, 80, 60, 0.045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(90, 80, 60, 0.045) 1px, transparent 1px);
  background-size: 44px 44px;
  mask-image: radial-gradient(ellipse 90% 70% at 50% 0%, #000 30%, transparent 78%);
  -webkit-mask-image: radial-gradient(ellipse 90% 70% at 50% 0%, #000 30%, transparent 78%);
}

.app-header {
  position: sticky;
  top: 12px;
  z-index: 60;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 14px;
  margin-bottom: 30px;
  border: 1px solid var(--border);
  border-radius: 18px;
  background: rgba(255, 253, 248, 0.78);
  backdrop-filter: blur(18px) saturate(1.4);
  -webkit-backdrop-filter: blur(18px) saturate(1.4);
  box-shadow: 0 10px 30px rgba(90, 80, 60, 0.12);
}

.app-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  color: var(--text);
  min-width: 0;
}

.brand-mark {
  width: 26px;
  height: 26px;
  border-radius: 9px;
  flex-shrink: 0;
  background: var(--accent-grad, linear-gradient(135deg, #c05621, #8a3a1e));
  box-shadow: 0 4px 14px rgba(192, 86, 33, 0.3);
  position: relative;
}

.brand-mark::after {
  content: "";
  position: absolute;
  inset: 7px;
  border-radius: 5px;
  background: rgba(255, 255, 255, 0.9);
  clip-path: polygon(50% 0, 100% 35%, 78% 100%, 22% 100%, 0 35%);
}

.brand-name {
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 0.02em;
  background: linear-gradient(90deg, #b4532a, #8a3a1e);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  white-space: nowrap;
}

.app-nav {
  display: flex;
  align-items: center;
  gap: 8px;
}

.app-nav a {
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 13.5px;
  font-weight: 500;
  padding: 7px 16px;
  border: 1px solid transparent;
  border-radius: 999px;
  transition: color 0.18s ease, background 0.18s ease, border-color 0.18s ease;
}

.app-nav a:hover {
  color: var(--text);
  background: rgba(192, 86, 33, 0.08);
}

.app-nav a.router-link-active {
  color: #3d3931;
  background: linear-gradient(135deg, rgba(201, 118, 66, 0.95), rgba(154, 63, 30, 0.95));
  box-shadow: 0 4px 16px rgba(192, 86, 33, 0.2);
}

@media (max-width: 640px) {
  .app-shell {
    padding: 14px 14px 56px;
  }

  .app-header {
    top: 8px;
    padding: 9px 12px;
  }

  .brand-name {
    font-size: 15px;
  }
}
</style>
