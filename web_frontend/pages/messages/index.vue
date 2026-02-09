<template>
  <div class="page-container">
    <van-nav-bar title="私信" left-arrow @click-left="navigateTo('/')" fixed placeholder />

    <!-- 会话列表 -->
    <van-pull-refresh v-model="refreshing" @refresh="onRefresh">
      <div v-if="loading && conversations.length === 0" class="loading-container">
        <van-loading size="24px">加载中...</van-loading>
      </div>

      <van-cell-group v-else-if="conversations.length > 0" inset class="conversation-list">
        <van-cell
          v-for="conv in conversations"
          :key="conv.user.id"
          clickable
          @click="navigateTo(`/messages/${conv.user.id}`)"
        >
          <template #icon>
            <van-badge :content="conv.unread_count > 0 ? conv.unread_count : ''" :max="99">
              <van-image
                round
                width="48"
                height="48"
                :src="getFileUrl(conv.user.avatar_path) || '/default-avatar.png'"
                class="avatar"
              />
            </van-badge>
          </template>
          <template #title>
            <div class="conv-header">
              <span class="nickname">{{ conv.user.nickname }}</span>
              <span v-if="conv.user.is_ai" class="ai-badge">AI</span>
            </div>
          </template>
          <template #label>
            <div class="conv-preview">
              <span class="last-message">
                {{ conv.last_message?.is_mine ? '我: ' : '' }}{{ conv.last_message?.content || '暂无消息' }}
              </span>
              <span class="time">{{ formatTime(conv.last_message?.created_at) }}</span>
            </div>
          </template>
        </van-cell>
      </van-cell-group>

      <van-empty v-else description="暂无私信" />
    </van-pull-refresh>
  </div>
</template>

<script setup lang="ts">
import { showToast } from 'vant'

interface UserBrief {
  id: number
  username: string
  nickname: string
  avatar_path: string | null
  is_ai: boolean
}

interface Conversation {
  user: UserBrief
  last_message: {
    id: number
    content: string
    created_at: string
    is_mine: boolean
  } | null
  unread_count: number
}

const api = useApi()
const authStore = useAuthStore()
const { getFileUrl } = useFileUrl()

const conversations = ref<Conversation[]>([])
const loading = ref(true)
const refreshing = ref(false)

// 检查登录状态
if (!authStore.isLoggedIn) {
  navigateTo('/login')
}

const loadConversations = async () => {
  try {
    const data = await api.get<{ conversations: Conversation[] }>('/messages/conversations')
    conversations.value = data.conversations
  } catch (error: any) {
    showToast(error.message || '加载失败')
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

const onRefresh = () => {
  loadConversations()
}

const formatTime = (dateStr: string | undefined) => {
  if (!dateStr) return ''
  
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  if (diff < 604800000) return `${Math.floor(diff / 86400000)}天前`
  
  return `${date.getMonth() + 1}/${date.getDate()}`
}

// WebSocket接收新消息
const ws = useWebSocket()

onMounted(() => {
  loadConversations()
  
  // 监听新消息（WebSocket连接由layout管理）
  ws.onMessage((data) => {
    if (data.type === 'new_message') {
      // 刷新会话列表
      loadConversations()
    }
  })
})
</script>

<style scoped>
.page-container {
  padding-bottom: 60px;
  min-height: 100vh;
  background: #f5f5f5;
}

.loading-container {
  display: flex;
  justify-content: center;
  padding: 40px;
}

.conversation-list {
  margin: 12px;
}

.avatar {
  margin-right: 12px;
}

.conv-header {
  display: flex;
  align-items: center;
  gap: 6px;
}

.nickname {
  font-size: 15px;
  font-weight: 500;
  color: #333;
}

.ai-badge {
  font-size: 10px;
  padding: 1px 4px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 4px;
}

.conv-preview {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 4px;
}

.last-message {
  flex: 1;
  font-size: 13px;
  color: #999;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 200px;
}

.time {
  font-size: 12px;
  color: #bbb;
  margin-left: 8px;
  flex-shrink: 0;
}
</style>
