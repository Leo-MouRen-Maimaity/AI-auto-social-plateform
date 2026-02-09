<template>
  <div class="post-card" @click="goToDetail">
    <!-- 作者信息 -->
    <div class="post-header">
      <van-image
        round
        width="40"
        height="40"
        :src="getFileUrl(post.author.avatar_path) || '/default-avatar.png'"
        fit="cover"
      />
      <div class="author-info">
        <div class="author-name">
          {{ post.author.nickname }}
          <van-tag v-if="post.author.is_ai" type="primary" size="mini">AI</van-tag>
        </div>
        <div class="post-time">{{ formatTime(post.created_at) }}</div>
      </div>
    </div>

    <!-- 帖子内容 -->
    <div class="post-content">
      <p class="content-text">{{ post.content }}</p>
      <van-image
        v-if="post.image_path"
        :src="getFileUrl(post.image_path)"
        fit="cover"
        class="post-image"
        @click.stop
      />
    </div>

    <!-- 底部操作 -->
    <div class="post-actions">
      <div class="action-item" @click.stop="$emit('like', post.id)">
        <van-icon
          :name="post.is_liked ? 'like' : 'like-o'"
          :color="post.is_liked ? '#ee0a24' : ''"
        />
        <span>{{ post.likes_count || '点赞' }}</span>
      </div>
      <div class="action-item">
        <van-icon name="chat-o" />
        <span>{{ post.comments_count || '评论' }}</span>
      </div>
      <div class="action-item">
        <van-icon name="share-o" />
        <span>分享</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
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

const props = defineProps<{
  post: Post
}>()

defineEmits<{
  like: [postId: number]
}>()

const router = useRouter()

const goToDetail = () => {
  router.push(`/post/${props.post.id}`)
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
</script>

<style scoped>
.post-card {
  background: #fff;
  margin: 12px;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
}

.post-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.author-info {
  flex: 1;
}

.author-name {
  font-size: 15px;
  font-weight: 500;
  color: #323233;
  display: flex;
  align-items: center;
  gap: 6px;
}

.post-time {
  font-size: 12px;
  color: #969799;
  margin-top: 2px;
}

.post-content {
  margin-bottom: 12px;
}

.content-text {
  font-size: 15px;
  line-height: 1.6;
  color: #323233;
  margin-bottom: 10px;
  word-break: break-word;
}

.post-image {
  width: 100%;
  max-height: 300px;
  border-radius: 8px;
  overflow: hidden;
}

.post-actions {
  display: flex;
  justify-content: space-around;
  padding-top: 12px;
  border-top: 1px solid #f5f5f5;
}

.action-item {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #969799;
  font-size: 13px;
  cursor: pointer;
}

.action-item:active {
  opacity: 0.7;
}
</style>
