<template>
  <div class="login-page">
    <van-nav-bar title="登录" left-arrow @click-left="router.back()" />

    <div class="login-content">
      <div class="logo">
        <van-icon name="chat-o" size="60" color="#1989fa" />
        <h1>AI社区</h1>
      </div>

      <van-form @submit="onSubmit">
        <van-cell-group inset>
          <van-field
            v-model="form.username"
            name="username"
            label="用户名"
            placeholder="请输入用户名"
            :rules="[{ required: true, message: '请输入用户名' }]"
          />
          <van-field
            v-model="form.password"
            type="password"
            name="password"
            label="密码"
            placeholder="请输入密码"
            :rules="[{ required: true, message: '请输入密码' }]"
          />
        </van-cell-group>

        <div class="submit-btn">
          <van-button
            round
            block
            type="primary"
            native-type="submit"
            :loading="loading"
          >
            登录
          </van-button>
        </div>
      </van-form>

      <div class="register-link">
        还没有账号？
        <router-link to="/register">立即注册</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { showToast } from 'vant'

definePageMeta({
  layout: false,
})

const router = useRouter()
const config = useRuntimeConfig()
const authStore = useAuthStore()

const form = ref({
  username: '',
  password: '',
})
const loading = ref(false)

const onSubmit = async () => {
  loading.value = true
  try {
    // 使用FormData格式提交（OAuth2规范）
    const formData = new URLSearchParams()
    formData.append('username', form.value.username)
    formData.append('password', form.value.password)

    const response = await fetch(`${config.public.apiBase}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData,
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || '登录失败')
    }

    const data = await response.json()
    authStore.setToken(data.access_token)
    await authStore.fetchUser()
    
    showToast('登录成功')
    router.push('/')
  } catch (error: any) {
    showToast(error.message || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  background: #f5f5f5;
}

.login-content {
  padding: 40px 20px;
}

.logo {
  text-align: center;
  margin-bottom: 40px;
}

.logo h1 {
  margin-top: 12px;
  font-size: 24px;
  color: #323233;
}

.submit-btn {
  margin: 24px 16px;
}

.register-link {
  text-align: center;
  font-size: 14px;
  color: #969799;
}

.register-link a {
  color: #1989fa;
  text-decoration: none;
}
</style>
