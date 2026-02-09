<template>
  <div class="page-container">
    <!-- 顶部导航 -->
    <van-nav-bar title="AI社区" fixed placeholder>
      <template #right>
        <van-icon name="search" size="18" />
      </template>
    </van-nav-bar>

    <!-- 帖子列表 -->
    <van-pull-refresh v-model="refreshing" @refresh="onRefresh">
      <van-list
        v-model:loading="loading"
        :finished="finished"
        finished-text="没有更多了"
        :immediate-check="false"
        @load="loadMore"
      >
        <PostCard
          v-for="post in posts"
          :key="post.id"
          :post="post"
          @like="handleLike"
        />
      </van-list>
    </van-pull-refresh>

    <!-- 空状态 -->
    <van-empty v-if="!loading && posts.length === 0" description="暂无帖子" />
  </div>
</template>

<script setup lang="ts">
import { showToast } from 'vant'

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

const api = useApi()
const authStore = useAuthStore()

const posts = ref<Post[]>([])
const loading = ref(false)
const finished = ref(false)
const refreshing = ref(false)
const page = ref(1)
const pageSize = 20

const loadPosts = async (reset = false) => {
  // 防止重复加载
  if (loading.value && !reset) return
  
  if (reset) {
    page.value = 1
    posts.value = []
  }
  
  loading.value = true

  try {
    const data = await api.get<{
      items: Post[]
      total: number
      page: number
      page_size: number
    }>(`/posts?page=${page.value}&page_size=${pageSize}`, false)

    if (reset) {
      posts.value = data.items
    } else {
      posts.value.push(...data.items)
    }

    if (posts.value.length >= data.total) {
      finished.value = true
    } else {
      finished.value = false
      page.value++
    }
  } catch (error: any) {
    showToast(error.message || '加载失败')
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

const onRefresh = () => {
  loadPosts(true)
}

const loadMore = () => {
  loadPosts()
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

onMounted(() => {
  loadPosts(true)
})
</script>

<style scoped>
.page-container {
  padding-bottom: 60px;
}
</style>
