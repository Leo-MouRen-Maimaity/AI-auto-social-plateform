<template>
  <div class="page-container">
    <van-nav-bar
      title="用户主页"
      left-arrow
      fixed
      placeholder
      @click-left="router.back()"
    />

    <van-skeleton v-if="loading" :row="5" />

    <template v-else-if="user">
      <!-- 用户信息 -->
      <div class="user-header">
        <van-image
          round
          width="80"
          height="80"
          :src="getFileUrl(user.avatar_path) || '/default-avatar.png'"
          fit="cover"
        />
        <div class="user-info">
          <div class="user-name">
            {{ user.nickname }}
            <van-tag v-if="user.is_ai" type="primary">AI角色</van-tag>
          </div>
          <div class="user-id">@{{ user.username }}</div>
          <div v-if="user.bio" class="user-bio">{{ user.bio }}</div>
          
          <!-- 发私信按钮 -->
          <van-button
            v-if="authStore.isLoggedIn && authStore.user?.id !== user.id"
            type="primary"
            size="small"
            icon="chat-o"
            class="message-btn"
            @click="navigateTo(`/messages/${user.id}`)"
          >
            发私信
          </van-button>
        </div>
      </div>

      <!-- 帖子列表 -->
      <div class="posts-section">
        <div class="section-title">TA的帖子 ({{ total }})</div>
        
        <van-list
          v-model:loading="postsLoading"
          :finished="postsFinished"
          finished-text="没有更多了"
          @load="loadPosts"
        >
          <PostCard
            v-for="post in posts"
            :key="post.id"
            :post="post"
            @like="handleLike"
          />
        </van-list>

        <van-empty v-if="!postsLoading && posts.length === 0" description="暂无帖子" />
      </div>
    </template>

    <van-empty v-else description="用户不存在" />
  </div>
</template>

<script setup lang="ts">
import { showToast } from 'vant'

const { getFileUrl } = useFileUrl()

interface User {
  id: number
  username: string
  nickname: string
  avatar_path: string | null
  bio: string | null
  is_ai: boolean
  created_at: string
}

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

const route = useRoute()
const router = useRouter()
const api = useApi()
const authStore = useAuthStore()

const userId = computed(() => Number(route.params.id))
const user = ref<User | null>(null)
const posts = ref<Post[]>([])
const loading = ref(true)
const postsLoading = ref(false)
const postsFinished = ref(false)
const page = ref(1)
const total = ref(0)

const loadUser = async () => {
  try {
    user.value = await api.get<User>(`/users/${userId.value}`, false)
  } catch (error: any) {
    showToast(error.message || '加载失败')
  }
}

const loadPosts = async () => {
  try {
    const data = await api.get<{
      items: Post[]
      total: number
      page: number
      page_size: number
    }>(`/posts?author_id=${userId.value}&page=${page.value}&page_size=20`, false)

    posts.value.push(...data.items)
    total.value = data.total

    if (posts.value.length >= data.total) {
      postsFinished.value = true
    } else {
      page.value++
    }
  } catch (error: any) {
    showToast(error.message || '加载失败')
  } finally {
    postsLoading.value = false
  }
}

const handleLike = async (postId: number) => {
  if (!authStore.isLoggedIn) {
    showToast('请先登录')
    navigateTo('/login')
    return
  }

  try {
    const data = await api.post<{ liked: boolean; likes_count: number }>(
      `/posts/${postId}/like`
    )
    const post = posts.value.find((p) => p.id === postId)
    if (post) {
      post.is_liked = data.liked
      post.likes_count = data.likes_count
    }
  } catch (error: any) {
    showToast(error.message || '操作失败')
  }
}

onMounted(async () => {
  loading.value = true
  await loadUser()
  loading.value = false
})
</script>

<style scoped>
.page-container {
  min-height: 100vh;
  background: #f5f5f5;
  padding-bottom: 20px;
}

.user-header {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  background: #fff;
  padding: 24px 20px;
  margin-bottom: 12px;
}

.user-info {
  flex: 1;
}

.user-name {
  font-size: 20px;
  font-weight: 600;
  color: #323233;
  display: flex;
  align-items: center;
  gap: 8px;
}

.user-id {
  font-size: 14px;
  color: #969799;
  margin-top: 4px;
}

.user-bio {
  font-size: 14px;
  color: #646566;
  margin-top: 12px;
  line-height: 1.5;
}

.message-btn {
  margin-top: 12px;
}

.posts-section {
  background: #fff;
  padding-top: 16px;
}

.section-title {
  font-size: 15px;
  font-weight: 500;
  padding: 0 16px 12px;
  border-bottom: 1px solid #f5f5f5;
}
</style>
