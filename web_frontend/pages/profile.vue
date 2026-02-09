<template>
  <div class="page-container">
    <van-nav-bar title="我的" fixed placeholder />

    <!-- 未登录状态 -->
    <div v-if="!authStore.isLoggedIn" class="not-logged-in">
      <van-icon name="user-circle-o" size="80" color="#ddd" />
      <p>登录后查看更多内容</p>
      <van-button type="primary" round @click="navigateTo('/login')">
        立即登录
      </van-button>
    </div>

    <!-- 已登录状态 -->
    <template v-else>
      <!-- 用户信息卡片 -->
      <div class="user-card">
        <van-image
          round
          width="70"
          height="70"
          :src="getFileUrl(authStore.user?.avatar_path) || '/default-avatar.png'"
          fit="cover"
        />
        <div class="user-info">
          <div class="user-name">{{ authStore.user?.nickname }}</div>
          <div class="user-id">@{{ authStore.user?.username }}</div>
          <div v-if="authStore.user?.bio" class="user-bio">
            {{ authStore.user.bio }}
          </div>
        </div>
      </div>

      <!-- 统计数据 -->
      <div class="stats-card">
        <div class="stat-item">
          <div class="stat-value">{{ myPostsCount }}</div>
          <div class="stat-label">帖子</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">0</div>
          <div class="stat-label">关注</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">0</div>
          <div class="stat-label">粉丝</div>
        </div>
      </div>

      <!-- 功能菜单 -->
      <van-cell-group inset class="menu-group">
        <van-cell title="我的帖子" is-link @click="showMyPosts = true">
          <template #icon>
            <van-icon name="notes-o" class="cell-icon" />
          </template>
        </van-cell>
        <van-cell title="我的收藏" is-link>
          <template #icon>
            <van-icon name="star-o" class="cell-icon" />
          </template>
        </van-cell>
        <van-cell title="消息通知" is-link>
          <template #icon>
            <van-icon name="bell" class="cell-icon" />
          </template>
        </van-cell>
        <van-cell title="设置" is-link>
          <template #icon>
            <van-icon name="setting-o" class="cell-icon" />
          </template>
        </van-cell>
      </van-cell-group>

      <!-- 退出登录 -->
      <div class="logout-btn">
        <van-button block plain type="danger" @click="handleLogout">
          退出登录
        </van-button>
      </div>
    </template>

    <!-- 我的帖子弹窗 -->
    <van-popup
      v-model:show="showMyPosts"
      position="bottom"
      :style="{ height: '80%' }"
      round
    >
      <div class="popup-header">
        <span>我的帖子</span>
        <van-icon name="cross" @click="showMyPosts = false" />
      </div>
      <div class="popup-content">
        <van-list
          v-model:loading="postsLoading"
          :finished="postsFinished"
          finished-text="没有更多了"
          @load="loadMyPosts"
        >
          <PostCard
            v-for="post in myPosts"
            :key="post.id"
            :post="post"
          />
        </van-list>
        <van-empty v-if="!postsLoading && myPosts.length === 0" description="暂无帖子" />
      </div>
    </van-popup>
  </div>
</template>

<script setup lang="ts">
import { showToast, showConfirmDialog } from 'vant'

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

const router = useRouter()
const api = useApi()
const authStore = useAuthStore()

const showMyPosts = ref(false)
const myPosts = ref<Post[]>([])
const myPostsCount = ref(0)
const postsLoading = ref(false)
const postsFinished = ref(false)
const postsPage = ref(1)

const loadMyPosts = async () => {
  if (!authStore.user) return

  try {
    const data = await api.get<{
      items: Post[]
      total: number
      page: number
      page_size: number
    }>(`/posts?author_id=${authStore.user.id}&page=${postsPage.value}&page_size=20`)

    myPosts.value.push(...data.items)
    myPostsCount.value = data.total

    if (myPosts.value.length >= data.total) {
      postsFinished.value = true
    } else {
      postsPage.value++
    }
  } catch (error: any) {
    showToast(error.message || '加载失败')
  } finally {
    postsLoading.value = false
  }
}

const handleLogout = async () => {
  try {
    await showConfirmDialog({
      title: '确认退出',
      message: '确定要退出登录吗？',
    })
    authStore.logout()
    showToast('已退出登录')
  } catch {
    // 用户取消
  }
}

watch(showMyPosts, (val) => {
  if (val && myPosts.value.length === 0) {
    loadMyPosts()
  }
})

onMounted(() => {
  if (authStore.isLoggedIn && authStore.user) {
    // 加载帖子数量
    api.get<{ items: Post[]; total: number }>(
      `/posts?author_id=${authStore.user.id}&page=1&page_size=1`
    ).then((data) => {
      myPostsCount.value = data.total
    }).catch(() => {})
  }
})
</script>

<style scoped>
.page-container {
  min-height: 100vh;
  background: #f5f5f5;
  padding-bottom: 60px;
}

.not-logged-in {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  text-align: center;
}

.not-logged-in p {
  margin: 20px 0;
  color: #969799;
}

.user-card {
  display: flex;
  align-items: center;
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
}

.user-id {
  font-size: 14px;
  color: #969799;
  margin-top: 4px;
}

.user-bio {
  font-size: 14px;
  color: #646566;
  margin-top: 8px;
}

.stats-card {
  display: flex;
  background: #fff;
  padding: 20px;
  margin-bottom: 12px;
}

.stat-item {
  flex: 1;
  text-align: center;
}

.stat-value {
  font-size: 20px;
  font-weight: 600;
  color: #323233;
}

.stat-label {
  font-size: 13px;
  color: #969799;
  margin-top: 4px;
}

.menu-group {
  margin-bottom: 12px;
}

.cell-icon {
  margin-right: 8px;
  font-size: 18px;
}

.logout-btn {
  padding: 20px;
}

.popup-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  font-size: 16px;
  font-weight: 500;
  border-bottom: 1px solid #eee;
}

.popup-content {
  height: calc(100% - 50px);
  overflow-y: auto;
}
</style>
