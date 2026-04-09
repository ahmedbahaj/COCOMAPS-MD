<template>
  <div class="examples-page">
    <header class="page-header">
      <h1>Examples</h1>
    </header>

    <main class="content">
      <div class="container" />
    </main>

    <AppFooter />
  </div>
</template>

<script setup>
import AppFooter from '../components/layout/AppFooter.vue'
</script>

<style scoped>
.examples-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f5f7;
}

.page-header {
  padding: 60px 40px 32px;
  text-align: center;
  background: linear-gradient(180deg, #ffffff 0%, #f5f5f7 100%);
}

.page-header h1 {
  font-size: 48px;
  font-weight: 700;
  color: #1d1d1f;
  margin: 0;
  letter-spacing: -0.02em;
}

.content {
  flex: 1;
  padding: 0 40px 80px;
}

.container {
  max-width: 960px;
  margin: 0 auto;
}

@media (max-width: 768px) {
  .page-header {
    padding: 40px 24px 24px;
  }

  .page-header h1 {
    font-size: 36px;
  }

  .content {
    padding: 0 24px 60px;
  }
}
</style>
