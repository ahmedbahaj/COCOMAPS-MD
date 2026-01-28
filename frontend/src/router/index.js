import { createRouter, createWebHistory } from 'vue-router'
import LandingPage from '../views/LandingPage.vue'
import Home from '../views/Home.vue'
import AboutPage from '../views/AboutPage.vue'
import ReferencesPage from '../views/ReferencesPage.vue'

const routes = [
  {
    path: '/',
    name: 'Landing',
    component: LandingPage
  },
  {
    path: '/analysis',
    name: 'Analysis',
    component: Home
  },
  {
    path: '/about',
    name: 'About',
    component: AboutPage
  },
  {
    path: '/references',
    name: 'References',
    component: ReferencesPage
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router

