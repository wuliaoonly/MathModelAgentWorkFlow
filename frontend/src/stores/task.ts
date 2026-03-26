import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { TaskWebSocket } from '@/utils/websocket'
import type { Message, CoderMessage, WriterMessage, UserMessage, ModelerMessage, CoordinatorMessage, InterpreterMessage } from '@/utils/response'
// import messageData from '@/test/20250524-115938-d4c84576.json'
import { AgentType } from '@/utils/enum'

export const useTaskStore = defineStore('task', () => {
  // 初始化时直接加载测试数据，确保页面首次渲染时有数据
  // const messages = ref<Message[]>(messageData as Message[])
  const messages = ref<Message[]>([])
  const currentTaskId = ref<string | null>(null) // legacy
  const currentProjectId = ref<string | null>(null)
  const currentRunId = ref<string | null>(null)
  const isConnected = ref(false)
  const reconnectAttempts = ref(0)
  let ws: TaskWebSocket | null = null

  type ConnectArgs =
    | { projectId: string; runId: string; autoReconnect?: boolean }
    | { taskId: string; autoReconnect?: boolean }

  // 连接 WebSocket
  async function connectWebSocket(args: ConnectArgs) {
    const baseUrl = import.meta.env.VITE_WS_URL
    const autoReconnect = ('autoReconnect' in args ? args.autoReconnect : undefined) ?? true
    const wsUrl =
      'projectId' in args
        ? `${baseUrl}/ws/projects/${args.projectId}/runs/${args.runId}`
        : `${baseUrl}/task/${args.taskId}`

    if ('projectId' in args) {
      currentProjectId.value = args.projectId
      currentRunId.value = args.runId
      localStorage.setItem('currentProjectId', args.projectId)
      localStorage.setItem('currentRunId', args.runId)
      currentTaskId.value = null
      localStorage.removeItem('currentTaskId')
    } else {
      currentTaskId.value = args.taskId
      localStorage.setItem('currentTaskId', args.taskId)
      currentProjectId.value = null
      currentRunId.value = null
      localStorage.removeItem('currentProjectId')
      localStorage.removeItem('currentRunId')
    }

    // 🔥 不再通过 HTTP API 加载历史消息，改为通过 WebSocket 接收
    // WebSocket 连接后，后端会自动发送所有历史消息

    // 如果已有连接，先关闭
    if (ws) {
      ws.close()
    }

    ws = new TaskWebSocket(
      wsUrl, 
      (data) => {
        console.log('📨 收到消息:', data)
        
        // 检查是否是重复消息（通过 id 去重）
        const isDuplicate = messages.value.some(msg => msg.id === data.id)
        if (!isDuplicate) {
          messages.value.push(data)
        } else {
          console.log('⚠️ 跳过重复消息:', data.id)
        }
        reconnectAttempts.value = 0 // 重置重连次数
      },
      (connected) => {
        isConnected.value = connected
        if (!connected && autoReconnect && reconnectAttempts.value < 5) {
          // 连接断开时尝试重连
          console.log(`🔄 连接断开，准备重连 (${reconnectAttempts.value + 1}/5)`)
          reconnectAttempts.value++
          setTimeout(() => {
            console.log('🔄 开始重连...')
            if (currentProjectId.value && currentRunId.value) {
              connectWebSocket({ projectId: currentProjectId.value, runId: currentRunId.value, autoReconnect: true })
              return
            }
            if (currentTaskId.value) {
              connectWebSocket({ taskId: currentTaskId.value, autoReconnect: true })
            }
          }, 3000 * reconnectAttempts.value) // 递增延迟
        }
      }
    )
    
    ws.connect()
  }


  // 从 localStorage 恢复任务
  async function restoreTask() {
    const savedProjectId = localStorage.getItem('currentProjectId')
    const savedRunId = localStorage.getItem('currentRunId')
    if (savedProjectId && savedRunId) {
      console.log('🔄 检测到未完成的 run，正在恢复:', savedProjectId, savedRunId)
      try {
        await connectWebSocket({ projectId: savedProjectId, runId: savedRunId, autoReconnect: true })
        return savedRunId
      } catch (error) {
        console.error('❌ 恢复 run 失败:', error)
        localStorage.removeItem('currentProjectId')
        localStorage.removeItem('currentRunId')
      }
    }

    const savedTaskId = localStorage.getItem('currentTaskId')
    if (savedTaskId) {
      console.log('🔄 检测到未完成的任务，正在恢复:', savedTaskId)
      try {
        // 检查任务是否存在
        const apiBaseUrl = import.meta.env.VITE_API_BASE_URL
        const response = await fetch(`${apiBaseUrl}/task/${savedTaskId}/info`)
        
        if (response.ok) {
          await connectWebSocket({ taskId: savedTaskId, autoReconnect: true })
          return savedTaskId
        } else {
          console.warn('⚠️ 任务不存在，清除缓存')
          localStorage.removeItem('currentTaskId')
        }
      } catch (error) {
        console.error('❌ 恢复任务失败:', error)
        localStorage.removeItem('currentTaskId')
      }
    }
    return null
  }

  // 清除当前任务
  function clearCurrentTask() {
    localStorage.removeItem('currentTaskId')
    localStorage.removeItem('currentProjectId')
    localStorage.removeItem('currentRunId')
    currentTaskId.value = null
    currentProjectId.value = null
    currentRunId.value = null
    messages.value = []
    reconnectAttempts.value = 0
    if (ws) {
      ws.close()
      ws = null
    }
  }

  // 关闭 WebSocket
  function closeWebSocket() {
    ws?.close()
  }

  function addUserMessage(content: string) {
    messages.value.push({
      id: Date.now().toString(),
      msg_type: 'user',
      content: content,
    } as UserMessage)
  }

  // 下载消息
  function downloadMessages() {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(messages.value, null, 2))
    const downloadAnchorNode = document.createElement('a')
    downloadAnchorNode.setAttribute("href", dataStr)
    downloadAnchorNode.setAttribute("download", "message.json")
    document.body.appendChild(downloadAnchorNode)
    downloadAnchorNode.click()
    downloadAnchorNode.remove()
  }

  // 计算属性
  const chatMessages = computed(() =>
    messages.value.filter(
      (msg) => {
        if (msg.msg_type === 'agent' && msg.agent_type === AgentType.CODER && msg.content != null && msg.content != '') {
          return true
        }
        if (msg.msg_type === 'user') {
          return true
        }
        if(msg.msg_type === 'system') {
          return true
        }
        // if (msg.msg_type === 'tool' && msg.tool_name === 'execute_code') {
          // return true
        // }
        return false
      }
    )
  )

  const coordinatorMessages = computed(() =>
    messages.value.filter(
      (msg): msg is CoordinatorMessage =>
        msg.msg_type === 'agent' &&
        msg.agent_type === AgentType.COORDINATOR &&
        msg.content != null
    )
  )

  const modelerMessages = computed(() =>
    messages.value.filter(
      (msg): msg is ModelerMessage =>
        msg.msg_type === 'agent' &&
        msg.agent_type === AgentType.MODELER &&
        msg.content != null
    )
  )

  const coderMessages = computed(() =>
    messages.value.filter(
      (msg): msg is CoderMessage =>
        msg.msg_type === 'agent' &&
        msg.agent_type === AgentType.CODER &&
        msg.content != null
    )
  )

  const writerMessages = computed(() =>
    messages.value.filter(
      (msg): msg is WriterMessage =>
        msg.msg_type === 'agent' &&
        msg.agent_type === AgentType.WRITER &&
        msg.content != null
    )
  )

  // 添加代码执行工具消息的计算属性
  const interpreterMessage = computed(() =>
    messages.value.filter(
      (msg): msg is InterpreterMessage =>
        msg.msg_type === 'tool' &&
        'tool_name' in msg &&
        msg.tool_name === 'execute_code'
    )
  )

  const files = computed(() => {
    // 反向遍历消息找到最新的文件列表
    for (let i = coderMessages.value.length - 1; i >= 0; i--) {
      const msg = coderMessages.value[i]
      if ('files' in msg && msg.files && Array.isArray(msg.files) && msg.files.length > 0) {
        console.log('找到文件列表:', msg.files)
        return msg.files
      }
    }
    // 如果没有找到文件列表，返回空数组
    console.log('没有找到文件列表，返回空数组')
    return []
  })
  
  // 初始化连接
  // 如果需要自动连接，可以在这里添加代码
  // 例如：connectWebSocket('default')

  return {
    messages,
    currentTaskId,
    currentProjectId,
    currentRunId,
    isConnected,
    reconnectAttempts,
    chatMessages,
    coordinatorMessages,
    modelerMessages,
    coderMessages,
    writerMessages,
    interpreterMessage,
    files,
    connectWebSocket,
    restoreTask,
    clearCurrentTask,
    closeWebSocket,
    downloadMessages,
    addUserMessage
  }
})
