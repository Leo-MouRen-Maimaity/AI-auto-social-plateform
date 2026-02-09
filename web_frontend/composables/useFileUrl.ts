// 获取完整的文件URL
export const useFileUrl = () => {
  const config = useRuntimeConfig()
  
  const getFileUrl = (path: string | null | undefined): string => {
    if (!path) return ''
    
    // 如果已经是完整URL，直接返回
    if (path.startsWith('http://') || path.startsWith('https://')) {
      return path
    }
    
    // 如果是 /files/ 开头的相对路径，拼接API base
    if (path.startsWith('/files/')) {
      return `${config.public.apiBase}${path}`
    }
    
    // 其他相对路径也拼接API base
    if (path.startsWith('/')) {
      return `${config.public.apiBase}${path}`
    }
    
    return path
  }
  
  return { getFileUrl }
}
