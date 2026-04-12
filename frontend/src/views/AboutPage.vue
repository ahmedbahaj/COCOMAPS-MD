<template>
  <div class="about-page">
    <!-- Header -->
    <header class="page-header">
      <h1>About COCOMAPS-MD</h1>
      <p class="subtitle">Understanding Protein-Protein Interface Interactions</p>
    </header>

    <!-- Main Content -->
    <main class="content">
      <div class="container">
        <section class="section">
          <h2>What is COCOMAPS-MD?</h2>
          <p>
            <strong>COCOMAPS-MD</strong> is a comprehensive tool for analyzing protein-protein
            and protein-nucleic acid interfaces across molecular dynamics trajectories.
            It identifies and classifies atomic interactions at molecular interfaces based
            on precise geometric criteria.
          </p>
          <p>
            Built on top of <strong>CoCoMaps 2.0</strong> (Contact and Contact Maps), this tool
            extends the capability to molecular dynamics (MD) trajectories, allowing researchers
            to study how interface contacts evolve over time and identify conserved interactions
            across simulation frames.
          </p>
        </section>
      </div>
    </main>

    <!-- Footer -->
    <AppFooter />
  </div>
</template>

<script setup>
import AppFooter from '../components/layout/AppFooter.vue'
</script>

<style scoped>
.about-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f5f7;
}

/* Header */
.page-header {
  padding: 60px 40px 40px;
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

.subtitle {
  font-size: 21px;
  color: #6e6e73;
  margin: 12px 0 0;
}

/* Content */
.content {
  flex: 1;
  padding: 0 40px 80px;
}

.container {
  max-width: 1000px;
  margin: 0 auto;
}

/* Sections */
.section {
  background: #ffffff;
  border-radius: 20px;
  padding: 40px;
  margin-bottom: 32px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.section h2 {
  font-size: 28px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 0 0 20px;
}

.section p {
  font-size: 17px;
  line-height: 1.6;
  color: #424245;
  margin: 0 0 16px;
}

.section p:last-child {
  margin-bottom: 0;
}

/* Responsive */
@media (max-width: 768px) {
  .page-header {
    padding: 40px 24px 32px;
  }

  .page-header h1 {
    font-size: 36px;
  }

  .content {
    padding: 0 24px 60px;
  }

  .section {
    padding: 28px;
  }
}
</style>
