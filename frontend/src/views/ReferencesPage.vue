<template>
  <div class="references-page">
    <!-- Navigation -->
    <nav class="nav-bar">
      <div class="nav-left">
        <router-link to="/" class="nav-logo">Trajectory Analysis</router-link>
        <div class="nav-links">
          <router-link to="/" class="nav-link">Home</router-link>
          <router-link to="/jobs" class="nav-link">Jobs</router-link>
          <router-link to="/about" class="nav-link">About</router-link>
          <router-link to="/references" class="nav-link active">References</router-link>
        </div>
      </div>
      <div class="nav-right"></div>
    </nav>

    <!-- Header -->
    <header class="page-header">
      <h1>References</h1>
      <p class="subtitle">Citations and Software Dependencies</p>
    </header>

    <!-- Main Content -->
    <main class="content">
      <div class="container">
        <!-- Citations -->
        <section class="section">
          <h2>How to Cite</h2>
          <p class="section-intro">
            If you use Trajectory Analysis in your research, please cite the following publication:
          </p>

          <div class="references-list">
            <div class="reference-card">
              <div class="reference-badge">Required</div>
              <h3>CoCoMaps 2.0</h3>
              <p class="authors">Chawla M., Kalra U., Petta A., Sharma S., Shaikh A.R., Cavallo L., Oliva R.</p>
              <p class="title">COCOMAPS 2.0: a web server for identifying, analyzing, and visualizing atomic interactions at the interface of biomolecular complexes</p>
              <p class="journal">Bioinformatics (2025) 41(12): btaf606</p>
            </div>
          </div>
        </section>

        <!-- BibTeX Section -->
        <section class="section bibtex-section">
          <h2>BibTeX Entry</h2>
          <div class="bibtex-container">
            <div class="bibtex-entry">
              <div class="bibtex-header">
                <span class="bibtex-label">CoCoMaps 2.0</span>
                <button class="copy-btn" @click="copyBibtex('cocomaps')">
                  <span v-if="copiedBib !== 'cocomaps'">Copy</span>
                  <span v-else>Copied!</span>
                </button>
              </div>
              <pre><code>{{ bibtexEntries.cocomaps }}</code></pre>
            </div>
          </div>
        </section>

        <!-- Core Dependencies -->
        <section class="section">
          <h2>Core Analysis Tools</h2>
          <p class="section-intro">
            Trajectory Analysis relies on CoCoMaps 2.0 and these established bioinformatics tools:
          </p>

          <div class="dependencies-grid">
            <div class="dependency-card">
              <h3>CoCoMaps 2.0</h3>
              <p class="description">Contact and Contact Maps - web application for analyzing biomolecular interfaces.</p>
              <p class="authors">Vangone A. et al.</p>
              <a href="https://aocdweb.com/BioTools/cocomaps2" target="_blank" class="link">Visit CoCoMaps 2.0 ↗</a>
            </div>

            <div class="dependency-card">
              <h3>HBPLUS</h3>
              <p class="version">v3.2</p>
              <p class="description">Hydrogen bond calculation program for 3D structures of proteins and nucleic acids.</p>
              <p class="authors">McDonald I.K. & Thornton J.M.</p>
              <a href="https://www.ebi.ac.uk/thornton-srv/software/HBPLUS/" target="_blank" class="link">Learn more ↗</a>
            </div>

            <div class="dependency-card">
              <h3>NACCESS</h3>
              <p class="version">v2.1.1</p>
              <p class="description">Solvent accessible surface area calculation for proteins and nucleic acids.</p>
              <p class="authors">Hubbard S.J. & Thornton J.M.</p>
              <a href="http://wolf.bms.umist.ac.uk/naccess/" target="_blank" class="link">Learn more ↗</a>
            </div>

            <div class="dependency-card">
              <h3>MDAnalysis</h3>
              <p class="version">Latest</p>
              <p class="description">Python library for analysis of molecular dynamics trajectories.</p>
              <p class="authors">Michaud-Agrawal N. et al.</p>
              <a href="https://www.mdanalysis.org/" target="_blank" class="link">Learn more ↗</a>
            </div>
          </div>
        </section>

        <!-- Software Dependencies -->
        <section class="section">
          <h2>Software Dependencies</h2>
          <p class="section-intro">
            This application is built with the following technologies:
          </p>

          <div class="tech-grid">
            <div class="tech-category">
              <h3>Frontend</h3>
              <ul>
                <li>
                  <strong>Vue.js 3</strong>
                  <span>Progressive JavaScript framework</span>
                </li>
                <li>
                  <strong>Vue Router</strong>
                  <span>Official router for Vue.js</span>
                </li>
                <li>
                  <strong>Pinia</strong>
                  <span>State management</span>
                </li>
                <li>
                  <strong>Highcharts</strong>
                  <span>Interactive charting library</span>
                </li>
                <li>
                  <strong>Plotly.js</strong>
                  <span>Scientific visualization</span>
                </li>
                <li>
                  <strong>Axios</strong>
                  <span>HTTP client</span>
                </li>
                <li>
                  <strong>Vite</strong>
                  <span>Build tool and dev server</span>
                </li>
              </ul>
            </div>

            <div class="tech-category">
              <h3>Backend</h3>
              <ul>
                <li>
                  <strong>Python 3</strong>
                  <span>Core programming language</span>
                </li>
                <li>
                  <strong>Flask</strong>
                  <span>Web framework</span>
                </li>
                <li>
                  <strong>Biopython</strong>
                  <span>Structural biology tools</span>
                </li>
                <li>
                  <strong>NumPy</strong>
                  <span>Numerical computing</span>
                </li>
                <li>
                  <strong>Pandas</strong>
                  <span>Data analysis</span>
                </li>
                <li>
                  <strong>SciPy</strong>
                  <span>Scientific computing</span>
                </li>
              </ul>
            </div>
          </div>
        </section>

        <!-- License -->
        <section class="section">
          <h2>License & Usage</h2>
          <p>
            Trajectory Analysis is provided for academic and research purposes. 
            Please ensure proper citation when using this tool in publications.
          </p>
          <p>
            For commercial use inquiries, please contact the development team.
          </p>
        </section>
      </div>
    </main>

    <!-- Footer -->
    <AppFooter />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import AppFooter from '../components/AppFooter.vue'

const copiedBib = ref(null)

const bibtexEntries = {
  cocomaps: `@article{chawla2025cocomaps,
  title={COCOMAPS 2.0: a web server for identifying, analyzing, and visualizing atomic interactions at the interface of biomolecular complexes},
  author={Chawla, Mohit and Kalra, Utkarsh and Petta, Andrea and Sharma, Suraj and Shaikh, Abdul Rajjak and Cavallo, Luigi and Oliva, Romina},
  journal={Bioinformatics},
  volume={41},
  number={12},
  pages={btaf606},
  year={2025},
  publisher={Oxford University Press}
}`
}

const copyBibtex = async (key) => {
  try {
    await navigator.clipboard.writeText(bibtexEntries[key])
    copiedBib.value = key
    setTimeout(() => {
      copiedBib.value = null
    }, 2000)
  } catch (err) {
    console.error('Failed to copy:', err)
  }
}
</script>

<style scoped>
.references-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f5f7;
}

/* Navigation */
.nav-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 40px;
  background: #ffffff;
  border-bottom: 1px solid #e8e8ed;
  position: sticky;
  top: 0;
  z-index: 100;
}

.nav-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.nav-logo {
  font-size: 20px;
  font-weight: 700;
  color: #1d1d1f;
  text-decoration: none;
}

.nav-links {
  display: flex;
  gap: 32px;
  margin-left: 32px;
}

.nav-link {
  font-size: 15px;
  font-weight: 500;
  color: #6e6e73;
  text-decoration: none;
  transition: color 0.15s ease;
  position: relative;
  padding-bottom: 4px;
}

.nav-link::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  width: 0;
  height: 2px;
  background: #1d1d1f;
  transition: width 0.15s ease;
}

.nav-link:hover,
.nav-link.active,
.nav-link.router-link-active {
  color: #1d1d1f;
}

.nav-link.active::after,
.nav-link.router-link-active::after {
  width: 100%;
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

.section-intro {
  margin-bottom: 32px !important;
}

/* References List */
.references-list {
  display: grid;
  gap: 20px;
}

.reference-card {
  padding: 28px;
  background: #f5f5f7;
  border-radius: 16px;
  position: relative;
}

.reference-badge {
  position: absolute;
  top: 20px;
  right: 20px;
  padding: 4px 12px;
  background: #1d1d1f;
  color: #ffffff;
  font-size: 12px;
  font-weight: 600;
  border-radius: 980px;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.reference-card h3 {
  font-size: 20px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 0 0 12px;
}

.reference-card .authors {
  font-size: 15px;
  color: #6e6e73;
  margin: 0 0 8px;
}

.reference-card .title {
  font-size: 16px;
  font-weight: 500;
  color: #1d1d1f;
  margin: 0 0 8px;
  font-style: italic;
}

.reference-card .journal {
  font-size: 14px;
  color: #6e6e73;
  margin: 0 0 16px;
}

.reference-actions {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.doi-link {
  font-size: 14px;
  font-weight: 500;
  color: #0066cc;
  text-decoration: none;
  transition: color 0.15s ease;
}

.doi-link:hover {
  color: #004499;
}

.copy-bib-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: #ffffff;
  border: 1px solid #e8e8ed;
  border-radius: 980px;
  font-size: 14px;
  font-weight: 500;
  color: #1d1d1f;
  cursor: pointer;
  font-family: inherit;
  transition: all 0.15s ease;
}

.copy-bib-btn:hover {
  background: #f5f5f7;
  border-color: #d2d2d7;
}

.copy-bib-btn .copied {
  color: #34c759;
}

/* BibTeX Section */
.bibtex-section {
  background: #1d1d1f;
}

.bibtex-section h2 {
  color: #ffffff;
}

.bibtex-container {
  display: grid;
  gap: 20px;
}

.bibtex-entry {
  background: #2d2d2f;
  border-radius: 12px;
  overflow: hidden;
}

.bibtex-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: #3d3d3f;
}

.bibtex-label {
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
}

.copy-btn {
  padding: 6px 12px;
  background: #0066cc;
  color: #ffffff;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  font-family: inherit;
  transition: background 0.15s ease;
}

.copy-btn:hover {
  background: #0055aa;
}

.bibtex-entry pre {
  margin: 0;
  padding: 16px;
  overflow-x: auto;
}

.bibtex-entry code {
  font-family: 'SF Mono', Monaco, 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.5;
  color: #86868b;
  white-space: pre;
}

/* Dependencies Grid */
.dependencies-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.dependency-card {
  padding: 24px;
  background: #f5f5f7;
  border-radius: 16px;
}

.dependency-card h3 {
  font-size: 18px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 0;
}

.dependency-card .version {
  font-size: 13px;
  color: #86868b;
  margin: 4px 0 12px;
}

.dependency-card .description {
  font-size: 15px;
  line-height: 1.5;
  color: #424245;
  margin: 0 0 8px;
}

.dependency-card .authors {
  font-size: 13px;
  color: #6e6e73;
  margin: 0 0 12px;
}

.dependency-card .link {
  font-size: 14px;
  font-weight: 500;
  color: #0066cc;
  text-decoration: none;
}

.dependency-card .link:hover {
  color: #004499;
}

/* Tech Grid */
.tech-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;
}

.tech-category {
  padding: 28px;
  background: #f5f5f7;
  border-radius: 16px;
}

.tech-category h3 {
  font-size: 18px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 0 0 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e8e8ed;
}

.tech-category ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.tech-category li {
  display: flex;
  flex-direction: column;
  padding: 10px 0;
  border-bottom: 1px solid #e8e8ed;
}

.tech-category li:last-child {
  border-bottom: none;
}

.tech-category li strong {
  font-size: 15px;
  font-weight: 600;
  color: #1d1d1f;
}

.tech-category li span {
  font-size: 13px;
  color: #6e6e73;
  margin-top: 2px;
}

/* Responsive */
@media (max-width: 768px) {
  .nav-bar {
    padding: 16px 24px;
  }

  .nav-links {
    gap: 20px;
  }

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

  .reference-actions {
    flex-direction: column;
    align-items: flex-start;
  }

  .dependencies-grid,
  .tech-grid {
    grid-template-columns: 1fr;
  }
}
</style>
