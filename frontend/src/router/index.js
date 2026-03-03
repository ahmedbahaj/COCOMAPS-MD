import { createRouter, createWebHistory } from 'vue-router'
import LandingPage from '../views/LandingPage.vue'
import Home from '../views/Home.vue'
import AboutPage from '../views/AboutPage.vue'
import ReferencesPage from '../views/ReferencesPage.vue'
import JobsPage from '../views/JobsPage.vue'

const routes = [
  {
    path: '/',
    name: 'Landing',
    component: LandingPage
  },
  {
    path: '/analysis/:jobId',
    name: 'Analysis',
    component: Home
  },
  {
    path: '/jobs',
    name: 'Jobs',
    component: JobsPage
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
  history: createWebHistory('/BioTools/trajectory_analysis'),
  routes
})

export default router

