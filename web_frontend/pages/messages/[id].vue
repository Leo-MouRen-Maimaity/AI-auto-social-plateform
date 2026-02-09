<template>
  <div class="chat-page">
    <van-nav-bar
      :title="otherUser?.nickname || '聊天'"
      left-arrow
      @click-left="navigateTo('/messages')"
      fixed
      placeholder
    >
      <template #right>
        <van-icon name="user-o" size="20" @click="navigateTo(`/user/${userId}`)" />
      </template>
    </van-nav-bar>

    <!-- 消息列表 -->
    <div ref="messageListRef" class="message-list" @scroll="onScroll">
      <div v-if="loadingMore" class="loading-more">
        <van-loading size="20px" />
      </div>
      
      <div v-for="msg in messages" :key="msg.id" :class="['message-item', msg.sender_id === authStore.user?.id ? 'mine' : 'other']">
        <van-image
          v-if="msg.sender_id !== authStore.user?.id"
          round
          width="36"
          height="36"
          :src="getFileUrl(otherUser?.avatar_path) || '/default-avatar.png'"
          class="avatar"
        />
        <div class="message-content">
          <div class="bubble">{{ msg.content }}</div>
          <div class="time">{{ formatTime(msg.created_at) }}</div>
        </div>
        <van-image
          v-if="msg.sender_id === authStore.user?.id"
          round
          width="36"
          height="36"
          :src="getFileUrl(authStore.user?.avatar_path) || '/default-avatar.png'"
          class="avatar"
        />
      </div>
      
      <van-empty v-if="!loading && messages.length === 0" description="暂无消息，开始聊天吧" />
    </div>

    <!-- 输入区域 -->
    <div class="input-area">
      <van-field
        v-model="inputText"
        type="textarea"
        rows="1"
        autosize
        placeholder="输入消息..."
        class="input-field"
        @keydown.enter.exact.prevent="sendMessage"
      />
      <van-button type="primary" size="small" :disabled="!inputText.trim()" @click="sendMessage">
        发送
      </van-button>
    </div>
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

interface Message {
  id: number
  sender_id: number
  receiver_id: number | null
  group_id: number | null
  content: string
  is_read: boolean
  created_at: string
  sender: UserBrief
}

const route = useRoute()
const api = useApi()
const authStore = useAuthStore()
const { getFileUrl } = useFileUrl()

const userId = computed(() => Number(route.params.id))
const otherUser = ref<UserBrief | null>(null)
const messages = ref<Message[]>([])
const loading = ref(true)
const loadingMore = ref(false)
const inputText = ref('')
const messageListRef = ref<HTMLElement | null>(null)
const page = ref(1)
const hasMore = ref(true)

// 检查登录状态
if (!authStore.isLoggedIn) {
  navigateTo('/login')
}

const loadMessages = async (loadMore = false) => {
  if (loadMore && !hasMore.value) return
  
  if (loadMore) {
    loadingMore.value = true
    page.value++
  }
  
  try {
    const data = await api.get<{
      items: Message[]
      total: number
      page: number
      page_size: number
      other_user: UserBrief
    }>(`/messages/history/${userId.value}?page=${page.value}`)
    
    otherUser.value = data.other_user
    
    if (loadMore) {
      // 加载更多历史消息，插入到前面
      messages.value = [...data.items, ...messages.value]
    } else {
      messages.value = data.items
    }
    
    hasMore.value = data.items.length >= data.page_size
    
    // 标记消息为已读
    await api.post(`/messages/read/${userId.value}`)
  } catch (error: any) {
    showToast(error.message || '加载失败')
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

const sendMessage = async () => {
  const content = inputText.value.trim()
  if (!content) return
  
  try {
    const newMsg = await api.post<Message>(`/messages/send/${userId.value}`, {
      content
    })
    
    messages.value.push(newMsg)
    inputText.value = ''
    
    // 滚动到底部
    nextTick(() => {
      scrollToBottom()
    })
  } catch (error: any) {
    showToast(error.message || '发送失败')
  }
}

const scrollToBottom = () => {
  if (messageListRef.value) {
    messageListRef.value.scrollTop = messageListRef.value.scrollHeight
  }
}

const onScroll = () => {
  if (messageListRef.value && messageListRef.value.scrollTop < 50 && !loadingMore.value && hasMore.value) {
    loadMessages(true)
  }
}

const formatTime = (dateStr: string) => {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  
  const isToday = date.toDateString() === now.toDateString()
  const hours = date.getHours().toString().padStart(2, '0')
  const minutes = date.getMinutes().toString().padStart(2, '0')
  
  if (isToday) {
    return `${hours}:${minutes}`
  }
  
  return `${date.getMonth() + 1}/${date.getDate()} ${hours}:${minutes}`
}

// WebSocket接收新消息
const ws = useWebSocket()

onMounted(() => {
  loadMessages()
  
  // 监听新消息（WebSocket连接由layout管理）
  ws.onMessage((data) => {
    if (data.type === 'new_message' && data.data.sender_id === userId.value) {
      messages.value.push(data.data)
      // 标记为已读
      api.post(`/messages/read/${userId.value}`)
      nextTick(() => {
        scrollToBottom()
      })
    }
  })
  
  // 初始滚动到底部
  nextTick(() => {
    scrollToBottom()
  })
})
</script>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f5f5f5;
}

.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  padding-top: 58px;
  padding-bottom: 70px;
}

.loading-more {
  display: flex;
  justify-content: center;
  padding: 12px;
}

.message-item {
  display: flex;
  align-items: flex-start;
  margin-bottom: 16px;
}

.message-item.mine {
  flex-direction: row-reverse;
}

.avatar {
  flex-shrink: 0;
}

.message-content {
  max-width: 70%;
  margin: 0 8px;
}

.bubble {
  padding: 10px 14px;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.5;
  word-break: break-word;
}

.other .bubble {
  background: white;
  color: #333;
  border-top-left-radius: 4px;
}

.mine .bubble {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-top-right-radius: 4px;
}

.time {
  font-size: 11px;
  color: #999;
  margin-top: 4px;
}

.mine .time {
  text-align: right;
}

.input-area {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  align-items: flex-end;
  padding: 8px 12px;
  background: white;
  border-top: 1px solid #eee;
  gap: 8px;
}

.input-field {
  flex: 1;
  background: #f5f5f5;
  border-radius: 20px;
  padding: 4px 0;
}

.input-field :deep(.van-field__control) {
  max-height: 80px;
}
</style>
