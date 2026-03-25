import request from '@/utils/request'

export interface TaskInfo {
  task_id: string
  created_at: number
  has_notebook: boolean
  has_result: boolean
  title: string
}

export interface TaskDetailInfo extends TaskInfo {
  has_docx: boolean
  files: Array<{
    name: string
    size: number
    modified_at: number
  }>
}

export interface TasksListResponse {
  tasks: TaskInfo[]
}

/**
 * 获取历史任务列表
 */
export const getTasksList = (limit: number = 50) => {
  return request.get<TasksListResponse>('/tasks', {
    params: { limit }
  })
}

/**
 * 获取单个任务的详细信息
 */
export const getTaskInfo = (taskId: string) => {
  return request.get<TaskDetailInfo>(`/task/${taskId}/info`)
}

/**
 * 获取任务的历史消息
 */
export const getTaskMessages = (taskId: string) => {
  return request.get(`/task/${taskId}/messages`)
}
