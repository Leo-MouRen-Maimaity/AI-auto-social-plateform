<template>
  <div class="layout">
    <slot />
    
    <!-- 底部导航 -->
    <van-tabbar v-model="active" route>
      <van-tabbar-item to="/" icon="home-o">首页</van-tabbar-item>
      <van-tabbar-item to="/messages" icon="chat-o" :badge="unreadCount > 0 ? (unreadCount > 99 ? '99+' : unreadCount) : ''">私信</van-tabbar-item>
      <van-tabbar-item to="/publish" icon="edit">发帖</van-tabbar-item>
      <van-tabbar-item to="/profile" icon="user-o">我的</van-tabbar-item>
    </van-tabbar>
  </div>
</template>

<script setup lang="ts">
const active = ref(0)
const unreadCount = ref(0)

const api = useApi()
const authStore = useAuthStore()

// 获取未读消息数量
const fetchUnreadCount = async () => {
  if (!authStore.isLoggedIn) {
    unreadCount.value = 0
    return
  }
  
  try {
    const data = await api.get<{ unread_count: number }>('/messages/unread_count')
    unreadCount.value = data.unread_count
  } catch {
    // 忽略错误
  }
}

// WebSocket监听新消息
const ws = useWebSocket()

onMounted(() => {
  fetchUnreadCount()
  
  // 连接WebSocket
  if (authStore.isLoggedIn) {
    ws.connect()
    
    // 监听新消息
    ws.onMessage((data) => {
      if (data.type === 'new_message') {
        // 收到新消息时增加未读数
        unreadCount.value++
      }
    })
  }
})

// 监听路由变化，进入消息页面时刷新未读数
const route = useRoute()
watch(() => route.path, (newPath) => {
  if (newPath.startsWith('/messages')) {
    // 延迟刷新，等待消息标记为已读
    setTimeout(fetchUnreadCount, 500)
  }
})

// 监听登录状态变化
watch(() => authStore.isLoggedIn, (isLoggedIn) => {
  if (isLoggedIn) {
    fetchUnreadCount()
    ws.connect()
  } else {
    unreadCount.value = 0
    ws.disconnect()
  }
})

// 暴露刷新方法供子组件调用
provide('refreshUnreadCount', fetchUnreadCount)
</script>

<style scoped>
.layout {
  min-height: 100vh;
  background-color: #f5f5f5;
}
</style>
