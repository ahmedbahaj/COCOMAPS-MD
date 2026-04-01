<template>
  <div class="help-page">
    <header class="page-header">
      <h1>Help</h1>
      <p class="subtitle">Guides and Documentation</p>
    </header>

    <!-- Tab Bar -->
    <nav class="docs-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        :class="['docs-tab', { active: activeTab === tab.id }]"
        @click="switchTab(tab.id)"
      >
        <span class="tab-icon" v-html="tab.icon"></span>
        {{ tab.label }}
      </button>
    </nav>

    <!-- Docs Layout -->
    <div class="docs-layout">
      <!-- Sidebar -->
      <aside :class="['docs-sidebar', { open: sidebarOpen }]" ref="sidebarEl">
        <div
          v-for="tab in tabs"
          :key="'sidebar-' + tab.id"
          :class="['docs-sidebar-panel', { active: activeTab === tab.id }]"
        >
          <h4 class="sidebar-heading">{{ tab.label }}</h4>
          <a
            v-for="section in tab.sections"
            :key="section.id"
            :href="'#' + section.id"
            :class="['sidebar-link', { active: activeSection === section.id }]"
            @click.prevent="scrollToSection(section.id)"
          >
            {{ section.title }}
          </a>
        </div>
      </aside>

      <!-- Mobile sidebar backdrop -->
      <div
        v-if="sidebarOpen"
        class="sidebar-backdrop"
        @click="sidebarOpen = false"
      ></div>

      <!-- Mobile sidebar toggle -->
      <button
        class="sidebar-toggle"
        @click="sidebarOpen = !sidebarOpen"
        :aria-label="sidebarOpen ? 'Close sidebar' : 'Open sidebar'"
      >
        <svg v-if="!sidebarOpen" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
        <svg v-else viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>

      <!-- Content Panels -->
      <main class="docs-content">
        <div
          v-for="tab in tabs"
          :key="'panel-' + tab.id"
          :class="['docs-panel', { active: activeTab === tab.id }]"
        >
          <div
            v-for="section in tab.sections"
            :key="section.id"
            :id="section.id"
            class="docs-section"
          >
            <div class="docs-section-card">
              <h2>{{ section.title }}</h2>
              <p class="section-description">{{ section.description }}</p>

              <!-- Subsections -->
              <div
                v-for="sub in section.subsections"
                :key="sub.heading"
                :class="['docs-subsection', { 'docs-card-media': sub.image }]"
              >
                <div class="docs-card-text">
                  <h3>{{ sub.heading }}</h3>
                  <p v-for="(para, pi) in sub.paragraphs" :key="pi">{{ para }}</p>
                  <ul v-if="sub.items && sub.items.length">
                    <li v-for="(item, ii) in sub.items" :key="ii">{{ item }}</li>
                  </ul>
                </div>
                <div v-if="sub.image" class="docs-card-image">
                  <div class="image-placeholder">
                    <span>{{ sub.imageAlt || 'Screenshot' }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const activeTab = ref('usage')
const activeSection = ref('')
const sidebarOpen = ref(false)
const sidebarEl = ref(null)
let observer = null

const tabs = [
  {
    id: 'usage',
    label: 'Usage',
    icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 013 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>',
    sections: [
      {
        id: 'usage-overview',
        title: 'Overview',
        description: 'Getting started with COCOMAPS-MD.',
        subsections: [
          {
            heading: 'Placeholder',
            paragraphs: ['Content will be added here.']
          }
        ]
      }
    ]
  },
  {
    id: 'results',
    label: 'Results',
    icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/><path d="M9 21V9"/></svg>',
    sections: [
      {
        id: 'results-overview',
        title: 'Overview',
        description: 'Understanding your analysis results.',
        subsections: [
          {
            heading: 'Placeholder',
            paragraphs: ['Content will be added here.']
          }
        ]
      }
    ]
  },
  {
    id: 'interactions',
    label: 'Interactions',
    icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="12" r="4"/><circle cx="16" cy="12" r="4"/></svg>',
    sections: [
      {
        id: 'interactions-overview',
        title: 'Overview',
        description: 'Types of molecular interactions detected.',
        subsections: [
          {
            heading: 'Placeholder',
            paragraphs: ['Content will be added here.']
          }
        ]
      }
    ]
  },
  {
    id: 'legends',
    label: 'Legends',
    icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>',
    sections: [
      {
        id: 'legends-overview',
        title: 'Overview',
        description: 'Color codes, symbols, and chart legends explained.',
        subsections: [
          {
            heading: 'Placeholder',
            paragraphs: ['Content will be added here.']
          }
        ]
      }
    ]
  }
]

function switchTab(tabId) {
  activeTab.value = tabId
  sidebarOpen.value = false
  router.replace({ query: { tab: tabId }, hash: '' })
  nextTick(() => {
    setupObserver()
    window.scrollTo({ top: 0, behavior: 'smooth' })
  })
}

function scrollToSection(sectionId) {
  const el = document.getElementById(sectionId)
  if (el) {
    el.scrollIntoView({ behavior: 'smooth' })
    sidebarOpen.value = false
  }
}

function setupObserver() {
  if (observer) observer.disconnect()

  const currentTab = tabs.find(t => t.id === activeTab.value)
  if (!currentTab) return

  const sectionEls = currentTab.sections
    .map(s => document.getElementById(s.id))
    .filter(Boolean)

  if (sectionEls.length === 0) return

  observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          activeSection.value = entry.target.id
        }
      }
    },
    { rootMargin: '-80px 0px -60% 0px', threshold: 0 }
  )

  sectionEls.forEach(el => observer.observe(el))
}

function restoreFromURL() {
  const tabParam = route.query.tab
  if (tabParam && tabs.some(t => t.id === tabParam)) {
    activeTab.value = tabParam
  }
  nextTick(() => {
    setupObserver()
    if (route.hash) {
      const id = route.hash.slice(1)
      const el = document.getElementById(id)
      if (el) {
        setTimeout(() => el.scrollIntoView({ behavior: 'smooth' }), 100)
      }
    }
  })
}

onMounted(() => {
  restoreFromURL()
})

onBeforeUnmount(() => {
  if (observer) observer.disconnect()
})

watch(() => route.query.tab, (newTab) => {
  if (newTab && newTab !== activeTab.value && tabs.some(t => t.id === newTab)) {
    activeTab.value = newTab
    nextTick(() => setupObserver())
  }
})
</script>

<style scoped>
.help-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f5f7;
}

/* ── Header ── */
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

.subtitle {
  font-size: 21px;
  color: #6e6e73;
  margin: 12px 0 0;
}

/* ── Tab Bar ── */
.docs-tabs {
  display: flex;
  justify-content: center;
  gap: 8px;
  padding: 0 40px 24px;
  background: transparent;
  position: sticky;
  top: 57px; /* below navbar */
  z-index: 50;
  background: #f5f5f7;
}

.docs-tab {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 22px;
  font-size: 15px;
  font-weight: 600;
  color: #6e6e73;
  background: #ffffff;
  border: 2px solid #e8e8ed;
  border-radius: 980px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.docs-tab:hover {
  color: #1d1d1f;
  border-color: #d2d2d7;
  background: #fafafa;
}

.docs-tab.active {
  color: #ffffff;
  background: #1d1d1f;
  border-color: #1d1d1f;
}

.tab-icon {
  display: inline-flex;
  align-items: center;
}

.docs-tab.active .tab-icon :deep(svg) {
  stroke: #ffffff;
}

/* ── Docs Layout ── */
.docs-layout {
  display: flex;
  gap: 0;
  max-width: 1320px;
  margin: 0 auto;
  padding: 0 40px 80px;
  width: 100%;
  position: relative;
}

/* ── Sidebar ── */
.docs-sidebar {
  width: 240px;
  flex-shrink: 0;
  position: sticky;
  top: 120px;
  align-self: flex-start;
  max-height: calc(100vh - 140px);
  overflow-y: auto;
  padding-right: 24px;
  scrollbar-width: thin;
  scrollbar-color: #d2d2d7 transparent;
}

.docs-sidebar::-webkit-scrollbar {
  width: 4px;
}

.docs-sidebar::-webkit-scrollbar-thumb {
  background: #d2d2d7;
  border-radius: 2px;
}

.docs-sidebar-panel {
  display: none;
}

.docs-sidebar-panel.active {
  display: block;
}

.sidebar-heading {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #86868b;
  margin: 0 0 12px;
  padding: 0 12px;
}

.sidebar-link {
  display: block;
  padding: 8px 12px;
  font-size: 14px;
  font-weight: 500;
  color: #6e6e73;
  text-decoration: none;
  border-radius: 8px;
  border-left: 3px solid transparent;
  transition: all 0.15s ease;
  margin-bottom: 2px;
}

.sidebar-link:hover {
  color: #1d1d1f;
  background: rgba(0, 0, 0, 0.03);
}

.sidebar-link.active {
  color: #1d1d1f;
  font-weight: 600;
  background: rgba(0, 0, 0, 0.04);
  border-left-color: #1d1d1f;
}

/* ── Mobile Sidebar ── */
.sidebar-backdrop {
  display: none;
}

.sidebar-toggle {
  display: none;
}

/* ── Content ── */
.docs-content {
  flex: 1;
  min-width: 0;
}

.docs-panel {
  display: none;
}

.docs-panel.active {
  display: block;
}

.docs-section {
  scroll-margin-top: 140px;
  margin-bottom: 32px;
}

.docs-section-card {
  background: #ffffff;
  border-radius: 20px;
  padding: 40px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.docs-section-card h2 {
  font-size: 28px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 0 0 8px;
  letter-spacing: -0.02em;
}

.section-description {
  font-size: 17px;
  line-height: 1.6;
  color: #6e6e73;
  margin: 0 0 28px;
}

/* ── Subsections ── */
.docs-subsection {
  margin-bottom: 28px;
  padding-bottom: 28px;
  border-bottom: 1px solid #f0f0f2;
}

.docs-subsection:last-child {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}

.docs-card-text h3 {
  font-size: 20px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 0 0 12px;
}

.docs-card-text p {
  font-size: 16px;
  line-height: 1.65;
  color: #424245;
  margin: 0 0 12px;
}

.docs-card-text p:last-child {
  margin-bottom: 0;
}

.docs-card-text ul {
  margin: 8px 0 0;
  padding-left: 24px;
}

.docs-card-text li {
  font-size: 16px;
  line-height: 1.65;
  color: #424245;
  margin-bottom: 6px;
}

/* ── Media Layout (text + image) ── */
.docs-card-media {
  display: flex;
  align-items: flex-start;
  gap: 32px;
}

.docs-card-media .docs-card-text {
  flex: 1;
  min-width: 0;
}

.docs-card-image {
  flex-shrink: 0;
  width: 340px;
}

.image-placeholder {
  width: 100%;
  aspect-ratio: 16 / 10;
  background: #f5f5f7;
  border: 2px dashed #d2d2d7;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #86868b;
  font-size: 14px;
  font-weight: 500;
}

/* ── Responsive ── */
@media (max-width: 992px) {
  .page-header {
    padding: 40px 24px 24px;
  }

  .page-header h1 {
    font-size: 36px;
  }

  .docs-tabs {
    padding: 0 24px 20px;
    gap: 6px;
    flex-wrap: wrap;
  }

  .docs-tab {
    padding: 8px 16px;
    font-size: 14px;
  }

  .docs-layout {
    padding: 0 24px 60px;
  }

  /* Off-canvas sidebar */
  .docs-sidebar {
    position: fixed;
    top: 0;
    left: 0;
    width: 280px;
    height: 100vh;
    max-height: 100vh;
    background: #ffffff;
    z-index: 200;
    padding: 24px;
    box-shadow: 4px 0 24px rgba(0, 0, 0, 0.12);
    transform: translateX(-100%);
    transition: transform 0.25s ease;
    border-radius: 0;
  }

  .docs-sidebar.open {
    transform: translateX(0);
  }

  .sidebar-backdrop {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.3);
    z-index: 199;
    animation: fadeIn 0.2s ease;
  }

  .sidebar-toggle {
    display: flex;
    align-items: center;
    justify-content: center;
    position: fixed;
    bottom: 24px;
    left: 24px;
    width: 48px;
    height: 48px;
    background: #1d1d1f;
    color: #ffffff;
    border: none;
    border-radius: 50%;
    cursor: pointer;
    z-index: 198;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
    transition: transform 0.15s ease, background 0.15s ease;
  }

  .sidebar-toggle:hover {
    background: #000000;
    transform: scale(1.05);
  }

  .docs-section-card {
    padding: 28px;
  }

  .docs-card-media {
    flex-direction: column;
  }

  .docs-card-image {
    width: 100%;
    max-width: 400px;
  }
}

@media (max-width: 600px) {
  .docs-tabs {
    gap: 4px;
  }

  .docs-tab {
    padding: 7px 12px;
    font-size: 13px;
    gap: 5px;
  }

  .tab-icon {
    display: none;
  }

  .docs-section-card {
    padding: 20px;
    border-radius: 16px;
  }

  .docs-section-card h2 {
    font-size: 22px;
  }

  .docs-card-text h3 {
    font-size: 18px;
  }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
</style>
