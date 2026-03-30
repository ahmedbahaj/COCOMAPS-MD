<template>
  <nav class="nav-bar">
    <div class="nav-left">
      <button
        v-if="showHamburger"
        class="hamburger-btn"
        :class="{ active: sidebarOpen }"
        @click="$emit('toggle-sidebar')"
      >
        <span></span>
        <span></span>
        <span></span>
      </button>
      <router-link to="/" class="nav-logo">COCOMAPS-MD</router-link>
      <div class="nav-links">
        <router-link to="/" class="nav-link" exact>Home</router-link>
        <router-link to="/jobs" class="nav-link">Jobs</router-link>
        <router-link to="/about" class="nav-link">About</router-link>
        <router-link to="/references" class="nav-link">References</router-link>
      </div>
    </div>
    <div class="nav-right">
      <slot name="right" />
    </div>
  </nav>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

defineProps({
  sidebarOpen: { type: Boolean, default: false }
})

defineEmits(['toggle-sidebar'])

const route = useRoute()
const showHamburger = computed(() => route.name === 'Analysis')
</script>

<style scoped>
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
.nav-link.router-link-active,
.nav-link.router-link-exact-active {
  color: #1d1d1f;
}

.nav-link.router-link-active::after,
.nav-link.router-link-exact-active::after {
  width: 100%;
}

/* Hamburger button (only visible on Analysis page) */
.hamburger-btn {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 5px;
  width: 36px;
  height: 36px;
  padding: 8px;
  background: #f5f5f7;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s ease;
}

.hamburger-btn:hover {
  background: #e8e8ed;
}

.hamburger-btn span {
  display: block;
  width: 100%;
  height: 2px;
  background: #1d1d1f;
  border-radius: 1px;
  transition: all 0.2s ease;
}

.hamburger-btn.active span:nth-child(1) {
  transform: rotate(45deg) translate(5px, 5px);
}

.hamburger-btn.active span:nth-child(2) {
  opacity: 0;
}

.hamburger-btn.active span:nth-child(3) {
  transform: rotate(-45deg) translate(5px, -5px);
}

@media (max-width: 768px) {
  .nav-bar {
    padding: 16px 24px;
  }

  .nav-links {
    gap: 20px;
  }
}
</style>
