<template>
  <NuxtLayout>
    <NuxtPage />
  </NuxtLayout>
</template>

<script setup lang="ts">
const authStore = useAuthStore()

onMounted(() => {
  authStore.init()
  if (authStore.token) {
    authStore.fetchUser()
  }
})
</script>
