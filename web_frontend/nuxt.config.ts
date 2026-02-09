export default defineNuxtConfig({
  compatibilityDate: '2024-11-01',
  devtools: { enabled: true },
  
  modules: [
    '@pinia/nuxt',
    '@vant/nuxt',
  ],

  css: [
    'vant/lib/index.css',
    '~/assets/css/main.scss',
  ],

  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000',
    },
  },

  app: {
    head: {
      title: 'AI社区',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no' },
        { name: 'description', content: 'AI社区 - 本地拟真AI社区平台' },
      ],
    },
  },

  vite: {
    css: {
      preprocessorOptions: {
        scss: {
          additionalData: '',
        },
      },
    },
  },
})
