<script setup lang="ts">
import Bubble from './Bubble.vue'
import SystemMessage from './SystemMessage.vue'
import { ref, watch, nextTick } from 'vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Send } from 'lucide-vue-next'
import type { Message } from '@/utils/response'
import { useTaskStore } from '@/stores/task'
import { useToast } from '@/components/ui/toast'

const props = defineProps<{ messages: Message[] }>()

const taskStore = useTaskStore()
const { toast } = useToast()

const inputValue = ref('')
const inputRef = ref<HTMLInputElement | null>(null)
const scrollRef = ref<HTMLDivElement | null>(null)

// 自动滚动到底部
const scrollToBottom = () => {
  nextTick(() => {
    if (scrollRef.value) {
      scrollRef.value.scrollTop = scrollRef.value.scrollHeight
    }
  })
}

// 监听消息变化，自动滚动到底部
watch(() => props.messages.length, () => {
  scrollToBottom()
})

const sendMessage = () => {
  if (!inputValue.value.trim()) return
  
  // 添加用户消息到本地显示
  taskStore.addUserMessage(inputValue.value)
  
  // 显示提示（因为当前系统不支持在任务运行中发送额外消息）
  toast({
    title: '消息已添加',
    description: '您的消息已添加到对话中。注意：当前系统不支持在任务运行中发送额外指令。',
  })
  
  inputValue.value = ''
  inputRef.value?.focus()
  scrollToBottom()
}
</script>

<template>
  <div class="flex h-full flex-col p-3">
    <div ref="scrollRef" class="flex-1 overflow-y-auto">
      <template v-for="message in props.messages" :key="message.id">
        <div class="mb-3">
          <!-- 用户消息 -->
          <Bubble v-if="message.msg_type === 'user'" type="user" :content="message.content || ''" />
          <!-- agent 消息（CoderAgent/WriterAgent，只显示 content） -->
          <Bubble v-else-if="message.msg_type === 'agent'" type="agent" :agentType="message.agent_type"
            :content="message.content || ''" />
          <!-- 系统消息 -->
          <SystemMessage v-else-if="message.msg_type === 'system'" :content="message.content || ''"
            :type="message.type" />
        </div>
      </template>
    </div>
    <form class="w-full max-w-2xl mx-auto flex items-center gap-2 pt-4" @submit.prevent="sendMessage">
      <Input ref="inputRef" v-model="inputValue" type="text" placeholder="请输入消息..." class="flex-1" autocomplete="off" />
      <Button type="submit" :disabled="!inputValue.trim()">
        <Send />
      </Button>
    </form>
  </div>
</template>

<style scoped>
/* 自定义滚动条样式 */
.overflow-y-auto::-webkit-scrollbar {
  width: 4px;
}

.overflow-y-auto::-webkit-scrollbar-track {
  @apply bg-transparent;
}

.overflow-y-auto::-webkit-scrollbar-thumb {
  @apply bg-gray-300 dark:bg-gray-600 rounded-full;
}

.overflow-y-auto::-webkit-scrollbar-thumb:hover {
  @apply bg-gray-400 dark:bg-gray-500;
}
</style>