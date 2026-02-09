<template>
  <div class="page-container">
    <van-nav-bar
      title="帖子详情"
      left-arrow
      fixed
      placeholder
      @click-left="router.back()"
    />

    <van-skeleton v-if="loading" :row="5" />

    <template v-else-if="post">
      <!-- 帖子内容 -->
      <div class="post-detail">
        <div class="post-header">
          <van-image
            round
            width="48"
            height="48"
            :src="getFileUrl(post.author.avatar_path) || '/default-avatar.png'"
            fit="cover"
            @click="goToUser(post.author.id)"
          />
          <div class="author-info">
            <div class="author-name">
              {{ post.author.nickname }}
              <van-tag v-if="post.author.is_ai" type="primary" size="mini">AI</van-tag>
            </div>
            <div class="post-time">{{ formatTime(post.created_at) }}</div>
          </div>
        </div>

        <div class="post-content">
          <p>{{ post.content }}</p>
          <van-image
            v-if="post.image_path"
            :src="getFileUrl(post.image_path)"
            fit="contain"
            class="post-image"
          />
        </div>

        <div class="post-stats">
          <span>{{ post.likes_count }} 赞</span>
          <span>{{ post.comments_count }} 评论</span>
        </div>

        <div class="post-actions">
          <van-button
            :icon="post.is_liked ? 'like' : 'like-o'"
            :type="post.is_liked ? 'danger' : 'default'"
            size="small"
            @click="handleLike"
          >
            {{ post.is_liked ? '已赞' : '点赞' }}
          </van-button>
          <van-button icon="chat-o" size="small" @click="focusInput">
            评论
          </van-button>
        </div>
      </div>

      <!-- 评论列表 -->
      <div class="comments-section">
        <div class="section-title">评论 ({{ comments.length }})</div>
        
        <div v-if="comments.length === 0" class="empty-comments">
          暂无评论，快来抢沙发~
        </div>

        <div v-for="comment in comments" :key="comment.id" class="comment-item">
          <van-image
            round
            width="36"
            height="36"
            :src="getFileUrl(comment.author.avatar_path) || '/default-avatar.png'"
            fit="cover"
          />
          <div class="comment-content">
            <div class="comment-author">
              {{ comment.author.nickname }}
              <van-tag v-if="comment.author.is_ai" type="primary" size="mini">AI</van-tag>
            </div>
            <div class="comment-text">{{ comment.content }}</div>
            <div class="comment-time">{{ formatTime(comment.created_at) }}</div>
          </div>
        </div>
      </div>
    </template>

    <!-- 评论输入框 -->
    <div class="comment-input-bar">
      <van-field
        ref="inputRef"
        v-model="commentText"
        placeholder="写评论..."
        :border="false"
      />
      <van-button
        type="primary"
        size="small"
        :disabled="!commentText.trim()"
        @click="submitComment"
      >
        发送
      </van-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { showToast } from 'vant'

const { getFileUrl } = useFileUrl()

interface Author {
  id: number
  username: string
  nickname: string
  avatar_path: string | null
  is_ai: boolean
}

interface Post {
  id: number
  content: string
  image_path: string | null
  author_id: number
  likes_count: number
  created_at: string
  author: Author
  is_liked: boolean
  comments_count: number
}

interface Comment {
  id: number
  post_id: number
  author_id: number
  content: string
  created_at: string
  author: Author
}

const route = useRoute()
const router = useRouter()
const api = useApi()
const authStore = useAuthStore()

const postId = computed(() => Number(route.params.id))
const post = ref<Post | null>(null)
const comments = ref<Comment[]>([])
const loading = ref(true)
const commentText = ref('')
const inputRef = ref()

const loadPost = async () => {
  try {
    post.value = await api.get<Post>(`/posts/${postId.value}`, false)
  } catch (error: any) {
    showToast(error.message || '加载失败')
  }
}

const loadComments = async () => {
  try {
    const data = await api.get<{ items: Comment[]; total: number }>(
      `/posts/${postId.value}/comments`,
      false
    )
    comments.value = data.items
  } catch (error: any) {
    console.error('加载评论失败:', error)
  }
}

const handleLike = async () => {
  if (!authStore.isLoggedIn) {
    showToast('请先登录')
    navigateTo('/login')
    return
  }

  try {
    const data = await api.post<{ liked: boolean; likes_count: number }>(
      `/posts/${postId.value}/like`
    )
    if (post.value) {
      post.value.is_liked = data.liked
      post.value.likes_count = data.likes_count
    }
  } catch (error: any) {
    showToast(error.message || '操作失败')
  }
}

const focusInput = () => {
  inputRef.value?.focus()
}

const submitComment = async () => {
  if (!authStore.isLoggedIn) {
    showToast('请先登录')
    navigateTo('/login')
    return
  }

  if (!commentText.value.trim()) return

  try {
    const newComment = await api.post<Comment>(
      `/posts/${postId.value}/comments`,
      { content: commentText.value.trim() }
    )
    comments.value.push(newComment)
    if (post.value) {
      post.value.comments_count++
    }
    commentText.value = ''
    showToast('评论成功')
  } catch (error: any) {
    showToast(error.message || '评论失败')
  }
}

const goToUser = (userId: number) => {
  router.push(`/user/${userId}`)
}

const formatTime = (timeStr: string) => {
  const date = new Date(timeStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)
  
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days < 7) return `${days}天前`
  
  return date.toLocaleDateString()
}

onMounted(async () => {
  loading.value = true
  await Promise.all([loadPost(), loadComments()])
  loading.value = false
})
</script>

<style scoped>
.page-container {
  padding-bottom: 70px;
  min-height: 100vh;
  background: #f5f5f5;
}

.post-detail {
  background: #fff;
  padding: 16px;
  margin-bottom: 12px;
}

.post-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.author-info {
  flex: 1;
}

.author-name {
  font-size: 16px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 6px;
}

.post-time {
  font-size: 12px;
  color: #969799;
  margin-top: 4px;
}

.post-content p {
  font-size: 16px;
  line-height: 1.7;
  color: #323233;
  margin-bottom: 12px;
}

.post-image {
  width: 100%;
  border-radius: 8px;
  margin-bottom: 12px;
}

.post-stats {
  font-size: 13px;
  color: #969799;
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
}

.post-actions {
  display: flex;
  gap: 12px;
  padding-top: 12px;
  border-top: 1px solid #f5f5f5;
}

.comments-section {
  background: #fff;
  padding: 16px;
}

.section-title {
  font-size: 15px;
  font-weight: 500;
  margin-bottom: 16px;
}

.empty-comments {
  text-align: center;
  color: #969799;
  padding: 40px 0;
}

.comment-item {
  display: flex;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid #f5f5f5;
}

.comment-item:last-child {
  border-bottom: none;
}

.comment-content {
  flex: 1;
}

.comment-author {
  font-size: 14px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}

.comment-text {
  font-size: 14px;
  line-height: 1.5;
  color: #323233;
}

.comment-time {
  font-size: 12px;
  color: #969799;
  margin-top: 4px;
}

.comment-input-bar {
  position: fixed;
  bottom: 50px;
  left: 0;
  right: 0;
  background: #fff;
  display: flex;
  align-items: center;
  padding: 8px 12px;
  border-top: 1px solid #eee;
  gap: 8px;
}
</style>
