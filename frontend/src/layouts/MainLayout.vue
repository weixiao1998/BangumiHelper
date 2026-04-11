<template>
  <el-container class="main-layout">
    <el-header class="header">
      <div class="logo" @click="router.push('/')">
        <el-icon size="24"><VideoPlay /></el-icon>
        <span>BangumiHelper</span>
      </div>

      <el-menu mode="horizontal" :default-active="route.path" router class="nav-menu">
        <el-menu-item index="/">
          <el-icon><Calendar /></el-icon>
          <span>番剧日历</span>
        </el-menu-item>
        <el-menu-item index="/subscriptions">
          <el-icon><Star /></el-icon>
          <span>我的订阅</span>
        </el-menu-item>
        <el-menu-item index="/search">
          <el-icon><Search /></el-icon>
          <span>搜索</span>
        </el-menu-item>
        <el-menu-item index="/downloaders">
          <el-icon><Download /></el-icon>
          <span>下载器</span>
        </el-menu-item>
      </el-menu>

      <div class="user-area">
        <el-dropdown>
          <span class="user-info">
            <el-avatar :size="32" icon="User" />
            <span class="username">{{ userStore.user?.username }}</span>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="router.push('/settings')">
                <el-icon><Setting /></el-icon>
                设置
              </el-dropdown-item>
              <el-dropdown-item divided @click="handleLogout">
                <el-icon><SwitchButton /></el-icon>
                退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-header>

    <el-main class="main-content">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

function handleLogout() {
  userStore.logout()
  router.push('/login')
}
</script>

<style scoped lang="scss">
.main-layout {
  height: 100vh;
}

.header {
  display: flex;
  align-items: center;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 20px;

  .logo {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 18px;
    font-weight: 600;
    color: var(--el-color-primary);
    cursor: pointer;
    margin-right: 40px;
  }

  .nav-menu {
    flex: 1;
    border-bottom: none;
  }

  .user-area {
    .user-info {
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;

      .username {
        font-size: 14px;
      }
    }
  }
}

.main-content {
  background: #f5f7fa;
  padding: 0;
  overflow-y: auto;
}
</style>
