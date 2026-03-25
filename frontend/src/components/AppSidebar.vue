<script setup lang="ts">
import { QQ_GROUP, TWITTER, GITHUB_LINK, BILLBILL, XHS, DISCORD } from '@/utils/const'
import NavUser from './NavUser.vue'
import { ref, onMounted, computed } from 'vue'
import { getTasksList, type TaskInfo } from '@/apis/tasksApi'
import { useRouter } from 'vue-router'

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  type SidebarProps,
  SidebarRail,
} from '@/components/ui/sidebar'

const props = defineProps<SidebarProps>()
const router = useRouter()

// 历史任务列表
const historicalTasks = ref<TaskInfo[]>([])
const isLoadingTasks = ref(false)

// 加载历史任务
const loadHistoricalTasks = async () => {
  try {
    isLoadingTasks.value = true
    const response = await getTasksList(20) // 获取最近20个任务
    historicalTasks.value = response.data.tasks
    console.log('✅ 加载历史任务成功:', historicalTasks.value.length)
  } catch (error) {
    console.error('❌ 加载历史任务失败:', error)
  } finally {
    isLoadingTasks.value = false
  }
}

// 格式化时间
const formatTime = (timestamp: number) => {
  const date = new Date(timestamp * 1000)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))
  
  if (days === 0) {
    return '今天'
  } else if (days === 1) {
    return '昨天'
  } else if (days < 7) {
    return `${days}天前`
  } else {
    return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
  }
}

// 跳转到任务详情页
const goToTask = (taskId: string) => {
  router.push(`/task/${taskId}`)
}

// 组件挂载时加载历史任务
onMounted(() => {
  loadHistoricalTasks()
})

const socialMedia = [
  {
    name: 'QQ',
    url: QQ_GROUP,
    icon: '/qq.svg',
  },
  {
    name: 'Twitter',
    url: TWITTER,
    icon: '/twitter.svg',
  },
  {
    name: 'GitHub',
    url: GITHUB_LINK,
    icon: '/github.svg',
  },
  {
    name: '哔哩哔哩',
    url: BILLBILL,
    icon: '/bilibili.svg',
  },
  {
    name: '小红书',
    url: XHS,
    icon: '/xiaohongshu.svg',
  },
  {
    name: 'Discord',
    url: DISCORD,
    icon: '/discord.svg',
  },
]

</script>

<template>
  <Sidebar v-bind="props">
    <SidebarHeader>
      <!-- 图标 -->
      <div class="flex items-center gap-2 h-15">
        <router-link to="/" class="flex items-center gap-2">
          <img src="@/assets/icon.png" alt="logo" class="w-10 h-10">
          <div class="text-lg font-bold">MathModelAgent</div>
        </router-link>
      </div>
    </SidebarHeader>
    <SidebarContent>
      <!-- 开始新任务 -->
      <SidebarGroup>
        <SidebarGroupLabel>开始</SidebarGroupLabel>
        <SidebarGroupContent>
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton as-child>
                <router-link to="/">开始新任务</router-link>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>

      <!-- 历史任务 -->
      <SidebarGroup>
        <SidebarGroupLabel>
          <div class="flex items-center justify-between w-full">
            <span>历史任务</span>
            <span v-if="isLoadingTasks" class="text-xs text-muted-foreground">加载中...</span>
          </div>
        </SidebarGroupLabel>
        <SidebarGroupContent>
          <SidebarMenu>
            <SidebarMenuItem v-if="historicalTasks.length === 0 && !isLoadingTasks">
              <div class="px-2 py-1 text-xs text-muted-foreground">暂无历史任务</div>
            </SidebarMenuItem>
            <SidebarMenuItem v-for="task in historicalTasks" :key="task.task_id">
              <SidebarMenuButton @click="goToTask(task.task_id)">
                <div class="flex flex-col items-start w-full overflow-hidden">
                  <div class="text-sm truncate w-full">{{ task.title }}</div>
                  <div class="text-xs text-muted-foreground">{{ formatTime(task.created_at) }}</div>
                </div>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>
    </SidebarContent>
    <SidebarRail />
    <SidebarFooter>
      <NavUser />
    </SidebarFooter>
    <SidebarFooter>
      <!-- 展示图标社交媒体  -->
      <div class="flex items-center gap-4 justify-centermb-4 border-t  border-light-purple pt-3">
        <a v-for="item in socialMedia" :href="item.url" target="_blank">
          <img :src="item.icon" :alt="item.name" width="24" height="24" class="icon">
        </a>
      </div>
    </SidebarFooter>
  </Sidebar>
</template>
