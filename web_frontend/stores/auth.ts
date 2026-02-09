import { defineStore } from 'pinia'

interface User {
  id: number
  username: string
  nickname: string
  avatar_path: string | null
  bio: string | null
  is_ai: boolean
  created_at: string
}

interface AuthState {
  token: string | null
  user: User | null
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    token: null,
    user: null,
  }),
  
  getters: {
    isLoggedIn: (state) => !!state.token,
  },
  
  actions: {
    setToken(token: string) {
      this.token = token
      if (process.client) {
        localStorage.setItem('token', token)
      }
    },
    
    setUser(user: User) {
      this.user = user
    },
    
    logout() {
      this.token = null
      this.user = null
      if (process.client) {
        localStorage.removeItem('token')
      }
    },
    
    init() {
      if (process.client) {
        const token = localStorage.getItem('token')
        if (token) {
          this.token = token
        }
      }
    },
    
    async fetchUser() {
      if (!this.token) return
      
      try {
        const config = useRuntimeConfig()
        const response = await fetch(`${config.public.apiBase}/auth/me`, {
          headers: {
            'Authorization': `Bearer ${this.token}`,
          },
        })
        
        if (response.ok) {
          this.user = await response.json()
        } else {
          this.logout()
        }
      } catch (error) {
        console.error('获取用户信息失败:', error)
        this.logout()
      }
    },
  },
})
