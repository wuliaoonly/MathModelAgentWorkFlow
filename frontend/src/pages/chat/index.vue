<script setup lang="ts">


import AppSidebar from '@/components/AppSidebar.vue'
import UserStepper from '@/components/UserStepper.vue'
import ModelingExamples from '@/components/ModelingExamples.vue'
import { onMounted, ref } from 'vue'
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from '@/components/ui/sidebar'
import { getHelloWorld } from '@/apis/commonApi'
import MoreDetail from '@/pages/chat/components/MoreDetail.vue'
import Button from '@/components/ui/button/Button.vue'
import ServiceStatus from '@/components/ServiceStatus.vue'
import { AppWindow, CircleEllipsis } from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import { getProjects } from '@/apis/projectsApi'
onMounted(() => {
  getHelloWorld().then((res) => {
    console.log(res.data)
  })
})


const isMoreDetailOpen = ref(false)

const router = useRouter()
const loadingRecentRuns = ref(false)
const recentRuns = ref<
  Array<{
    project_id: string
    run_id: string
    status: string
    title: string | null
    created_at: number
  }>
>([])

const formatTime = (ms: number) => {
  try {
    return new Date(ms).toLocaleString()
  } catch {
    return ''
  }
}

const refreshRecentRuns = async () => {
  loadingRecentRuns.value = true
  try {
    const res = await getProjects(10)
    const items = (res.data?.projects ?? []).flatMap((p: any) => {
      if (!p?.latest_run?.run_id) return []
      return [
        {
          project_id: p.project_id,
          run_id: p.latest_run.run_id,
          status: p.latest_run.status,
          title: p.latest_run.title ?? null,
          created_at: p.latest_run.created_at ?? 0,
        },
      ]
    })
    items.sort((a, b) => (b.created_at || 0) - (a.created_at || 0))
    recentRuns.value = items.slice(0, 8)
  } catch (e) {
    console.error('加载最近 runs 失败:', e)
    recentRuns.value = []
  } finally {
    loadingRecentRuns.value = false
  }
}

const openRun = (item: { project_id: string; run_id: string }) => {
  router.push(`/projects/${item.project_id}/runs/${item.run_id}`)
}

onMounted(() => {
  refreshRecentRuns()
})

</script>

<template>

  <SidebarProvider>
    <MoreDetail v-model="isMoreDetailOpen" />
    <AppSidebar />
    <SidebarInset>
      <header class="flex h-16 shrink-0 items-center gap-2 px-4">
        <SidebarTrigger class="-ml-1" />
        <div class="flex justify-between w-full gap-2">
          <ServiceStatus />
          <div class="flex gap-2">
            <Button variant="outline" @click="isMoreDetailOpen = true">
              <CircleEllipsis />
              更多
            </Button>
            <a href="https://www.mathmodel.top/" target="_blank">
              <Button variant="outline">
                <AppWindow />
                官网
              </Button>
            </a>
          </div>
        </div>
      </header>

      <div class="py-5 px-4">
        <div class="space-y-6">
          <div class="text-center space-y-2 mb-10">
            <h1 class="text-2xl font-semibold">MathModelAgent</h1>
            <p class="text-muted-foreground">
              让 Agent 数学建模，代码编写，论文写作
            </p>
          </div>

          <div
            class="rounded-lg border bg-white p-4 shadow-sm"
            v-if="recentRuns.length > 0 || loadingRecentRuns"
          >
            <div class="flex items-center justify-between mb-3">
              <h3 class="text-sm font-semibold text-gray-900">最近 runs</h3>
              <Button
                variant="outline"
                size="sm"
                :disabled="loadingRecentRuns"
                @click="refreshRecentRuns"
              >
                刷新
              </Button>
            </div>

            <div v-if="loadingRecentRuns" class="text-sm text-gray-500">
              加载中...
            </div>

            <div v-else class="space-y-2 max-h-64 overflow-auto pr-1">
              <div
                v-for="run in recentRuns"
                :key="run.project_id + ':' + run.run_id"
                class="p-2 rounded hover:bg-slate-50 cursor-pointer border"
                @click="openRun(run)"
              >
                <div class="flex items-center justify-between gap-2">
                  <div class="min-w-0">
                    <div class="text-xs font-medium text-gray-800 truncate">
                      {{ run.title || run.run_id.slice(0, 8) }}
                    </div>
                    <div class="text-[11px] text-gray-500 truncate mt-1">
                      project={{ run.project_id.slice(0, 8) }}..., run={{ run.run_id.slice(0, 8) }}...
                    </div>
                  </div>
                  <div class="text-[11px] text-gray-400 whitespace-nowrap">
                    {{ formatTime(run.created_at) }}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <UserStepper>
          </UserStepper>
          <div class="text-center text-xs text-muted-foreground mt-8">
            项目处于内测阶段，欢迎进群反馈
          </div>
          <ModelingExamples />
        </div>
      </div>
    </SidebarInset>
  </SidebarProvider>
</template>
