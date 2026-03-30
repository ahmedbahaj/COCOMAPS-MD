<template>
  <div id="app">
    <RouterView />
  </div>
</template>

<script setup>
import { RouterView } from 'vue-router'
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', system-ui, sans-serif;
  background-color: #ffffff;
  color: #1d1d1f;
  line-height: 1.47059;
  font-weight: 400;
  letter-spacing: -0.022em;
}

#app {
  min-height: 100vh;
}

/* Hide app chrome when the Mol* viewer is expanded */
body.molstar-expanded .chart-selector,
body.molstar-expanded .nav-bar {
  display: none !important;
}
</style>

