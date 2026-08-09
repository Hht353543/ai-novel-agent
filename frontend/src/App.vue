<template>
  <div class="app-shell">
    <header class="app-header">
      <h1>AI 网文作者 Agent</h1>
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

body {
  font-family: "PingFang SC", "Microsoft YaHei", "Helvetica Neue", Arial, sans-serif;
  background: #0f1220;
  color: #e8eaf0;
  min-height: 100vh;
}

.app-shell {
  max-width: 980px;
  margin: 0 auto;
  padding: 32px 20px 64px;
}

.app-header {
  text-align: center;
  margin-bottom: 32px;
}

.app-header h1 {
  font-size: 28px;
  background: linear-gradient(90deg, #6ea8ff, #b388ff);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.app-header p {
  margin-top: 8px;
  color: #9aa3b5;
  font-size: 14px;
}

.app-nav {
  margin-top: 14px;
  display: flex;
  justify-content: center;
  gap: 18px;
}

.app-nav a {
  color: #9aa3b5;
  text-decoration: none;
  font-size: 14px;
  padding: 6px 14px;
  border: 1px solid #262c45;
  border-radius: 999px;
}

.app-nav a:hover,
.app-nav a.router-link-active {
  color: #6ea8ff;
  border-color: #6ea8ff;
}
</style>
