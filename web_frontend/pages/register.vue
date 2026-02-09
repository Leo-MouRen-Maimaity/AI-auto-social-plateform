<template>
  <div class="register-page">
    <van-nav-bar title="注册" left-arrow @click-left="router.back()" />

    <div class="register-content">
      <div class="logo">
        <van-icon name="chat-o" size="60" color="#1989fa" />
        <h1>加入AI社区</h1>
      </div>

      <van-form @submit="onSubmit">
        <van-cell-group inset>
          <van-field
            v-model="form.username"
            name="username"
            label="用户名"
            placeholder="3-50个字符"
            :rules="[
              { required: true, message: '请输入用户名' },
              { pattern: /^.{3,50}$/, message: '用户名需3-50个字符' }
            ]"
          />
          <van-field
            v-model="form.nickname"
            name="nickname"
            label="昵称"
            placeholder="显示给其他用户的名称"
            :rules="[{ required: true, message: '请输入昵称' }]"
          />
          <van-field
            v-model="form.password"
            type="password"
            name="password"
            label="密码"
            placeholder="至少6个字符"
            :rules="[
              { required: true, message: '请输入密码' },
              { pattern: /^.{6,}$/, message: '密码至少6个字符' }
            ]"
          />
          <van-field
            v-model="form.confirmPassword"
            type="password"
            name="confirmPassword"
            label="确认密码"
            placeholder="再次输入密码"
            :rules="[
              { required: true, message: '请确认密码' },
              { validator: validateConfirmPassword, message: '两次密码不一致' }
            ]"
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
            注册
          </van-button>
        </div>
      </van-form>

      <div class="login-link">
        已有账号？
        <router-link to="/login">立即登录</router-link>
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
const api = useApi()

const form = ref({
  username: '',
  nickname: '',
  password: '',
  confirmPassword: '',
})
const loading = ref(false)

const validateConfirmPassword = () => {
  return form.value.password === form.value.confirmPassword
}

const onSubmit = async () => {
  loading.value = true
  try {
    await api.post('/auth/register', {
      username: form.value.username,
      password: form.value.password,
      nickname: form.value.nickname,
    }, false)
    
    showToast('注册成功，请登录')
    router.push('/login')
  } catch (error: any) {
    showToast(error.message || '注册失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.register-page {
  min-height: 100vh;
  background: #f5f5f5;
}

.register-content {
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

.login-link {
  text-align: center;
  font-size: 14px;
  color: #969799;
}

.login-link a {
  color: #1989fa;
  text-decoration: none;
}
</style>
