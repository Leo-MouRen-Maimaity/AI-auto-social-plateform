// WebSocket连接封装 - 全局单例模式
// 使用共享状态确保整个应用只有一个WebSocket连接

let ws: WebSocket | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | null = null
let pingTimer: ReturnType<typeof setInterval> | null = null
const isConnected = ref(false)
const messageHandlers = new Set<(data: any) => void>()

export const useWebSocket = () => {
  const config = useRuntimeConfig()
  const authStore = useAuthStore()
  
  const connect = () => {
    // 如果已连接或正在连接，不重复创建
    if (!authStore.token || ws?.readyState === WebSocket.OPEN || ws?.readyState === WebSocket.CONNECTING) {
      return
    }
    
    // 构建WebSocket URL
    const wsBase = config.public.apiBase.replace('http://', 'ws://').replace('https://', 'wss://')
    const wsUrl = `${wsBase}/messages/ws?token=${authStore.token}`
    
    try {
      ws = new WebSocket(wsUrl)
      
      ws.onopen = () => {
        console.log('WebSocket connected')
        isConnected.value = true
        
        // 启动心跳
        if (pingTimer) clearInterval(pingTimer)
        pingTimer = setInterval(() => {
          if (ws?.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }))
          }
        }, 30000)
      }
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type !== 'pong') {
            messageHandlers.forEach(handler => handler(data))
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message', e)
        }
      }
      
      ws.onclose = () => {
        console.log('WebSocket disconnected')
        isConnected.value = false
        cleanup()
        
        // 自动重连
        if (authStore.token) {
          reconnectTimer = setTimeout(connect, 3000)
        }
      }
      
      ws.onerror = (error) => {
        console.error('WebSocket error', error)
      }
    } catch (e) {
      console.error('Failed to create WebSocket', e)
    }
  }
  
  const disconnect = () => {
    cleanup()
    if (ws) {
      ws.close()
      ws = null
    }
  }
  
  const cleanup = () => {
    if (pingTimer) {
      clearInterval(pingTimer)
      pingTimer = null
    }
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
  }
  
  const onMessage = (handler: (data: any) => void) => {
    messageHandlers.add(handler)
    // 返回取消订阅函数
    return () => {
      messageHandlers.delete(handler)
    }
  }
  
  return {
    connect,
    disconnect,
    isConnected,
    onMessage
  }
}
