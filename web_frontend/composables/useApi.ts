// API请求封装
export const useApi = () => {
  const config = useRuntimeConfig()
  const authStore = useAuthStore()
  
  const baseURL = config.public.apiBase

  const request = async <T>(
    url: string,
    options: {
      method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
      body?: any
      auth?: boolean
    } = {}
  ): Promise<T> => {
    const { method = 'GET', body, auth = true } = options
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }
    
    if (auth && authStore.token) {
      headers['Authorization'] = `Bearer ${authStore.token}`
    }
    
    const fetchOptions: any = {
      method,
      headers,
    }
    
    if (body && method !== 'GET') {
      fetchOptions.body = JSON.stringify(body)
    }
    
    const response = await fetch(`${baseURL}${url}`, fetchOptions)
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: '请求失败' }))
      throw new Error(error.detail || '请求失败')
    }
    
    // 204 No Content
    if (response.status === 204) {
      return null as T
    }
    
    return response.json()
  }

  return {
    get: <T>(url: string, auth = true) => request<T>(url, { method: 'GET', auth }),
    post: <T>(url: string, body?: any, auth = true) => request<T>(url, { method: 'POST', body, auth }),
    put: <T>(url: string, body?: any, auth = true) => request<T>(url, { method: 'PUT', body, auth }),
    delete: <T>(url: string, auth = true) => request<T>(url, { method: 'DELETE', auth }),
  }
}
