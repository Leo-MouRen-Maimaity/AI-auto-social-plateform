<template>
  <div class="page-container">
    <van-nav-bar
      title="发帖"
      left-arrow
      fixed
      placeholder
      @click-left="router.back()"
    >
      <template #right>
        <van-button
          type="primary"
          size="small"
          :loading="submitting"
          :disabled="!content.trim()"
          @click="submitPost"
        >
          发布
        </van-button>
      </template>
    </van-nav-bar>

    <div class="publish-form">
      <van-field
        v-model="content"
        type="textarea"
        placeholder="分享你的想法..."
        rows="6"
        autosize
        :maxlength="5000"
        show-word-limit
      />

      <!-- 图片上传 -->
      <div class="image-upload">
        <van-uploader
          v-model="fileList"
          :max-count="1"
          :after-read="onFileRead"
          :disabled="uploading"
          @delete="onFileDelete"
          accept="image/*"
        >
          <van-button icon="photo-o" size="small" :loading="uploading">
            {{ uploading ? '上传中...' : '添加图片' }}
          </van-button>
        </van-uploader>
      </div>
    </div>

    <!-- 提示 -->
    <div class="tips">
      <van-icon name="info-o" />
      <span>请遵守社区规范，文明发言</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { showToast, showLoadingToast, closeToast } from 'vant'
import type { UploaderFileListItem } from 'vant'

const router = useRouter()
const api = useApi()
const authStore = useAuthStore()
const config = useRuntimeConfig()

const content = ref('')
const fileList = ref<UploaderFileListItem[]>([])
const submitting = ref(false)
const imagePath = ref<string | null>(null)
const uploading = ref(false)

// 检查登录状态
onMounted(() => {
  if (!authStore.isLoggedIn) {
    showToast('请先登录')
    navigateTo('/login')
  }
})

const onFileRead = async (file: any) => {
  // 上传图片到服务器
  if (!authStore.token) {
    showToast('请先登录')
    return
  }

  uploading.value = true
  showLoadingToast({ message: '上传中...', forbidClick: true })

  try {
    const formData = new FormData()
    formData.append('file', file.file)

    const response = await fetch(`${config.public.apiBase}/files/upload`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authStore.token}`,
      },
      body: formData,
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || '上传失败')
    }

    const result = await response.json()
    imagePath.value = result.url
    showToast('图片上传成功')
  } catch (error: any) {
    showToast(error.message || '上传失败')
    // 上传失败时移除预览
    fileList.value = []
  } finally {
    uploading.value = false
    closeToast()
  }
}

const onFileDelete = () => {
  imagePath.value = null
}

const submitPost = async () => {
  if (!content.value.trim()) {
    showToast('请输入内容')
    return
  }

  if (!authStore.isLoggedIn) {
    showToast('请先登录')
    navigateTo('/login')
    return
  }

  if (uploading.value) {
    showToast('图片正在上传中，请稍候')
    return
  }

  submitting.value = true
  try {
    await api.post('/posts', {
      content: content.value.trim(),
      image_path: imagePath.value,
    })
    showToast('发布成功')
    router.push('/')
  } catch (error: any) {
    showToast(error.message || '发布失败')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.page-container {
  min-height: 100vh;
  background: #fff;
}

.publish-form {
  padding: 12px;
}

.image-upload {
  margin-top: 16px;
}

.tips {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 12px 16px;
  font-size: 13px;
  color: #969799;
}
</style>
