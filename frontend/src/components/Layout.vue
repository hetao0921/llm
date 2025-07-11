<template>
  <div class="app-wrapper">
    <div class="sidebar-container">
      <AppSidebar />
    </div>
    <div class="main-container">
      <div class="content-wrapper">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </div>
  </div>
</template>

<script>
import AppSidebar from './layout/AppSidebar.vue'

export default {
  name: 'Layout',
  components: {
    AppSidebar
  }
}
</script>

<style scoped>
.app-wrapper {
  position: relative;
  width: 100%;
  height: 100vh;
  display: flex;
}

.sidebar-container {
  width: 210px;
  height: 100%;
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  background-color: #001529;
  z-index: 1001;
}

.main-container {
  min-height: 100%;
  margin-left: 210px;
  position: relative;
  flex: 1;
  background-color: #f0f2f5;
}

.content-wrapper {
  padding: 20px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style> 