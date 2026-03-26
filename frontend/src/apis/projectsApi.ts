import request from "@/utils/request";

export interface LatestRun {
  run_id: string;
  project_id?: string;
  status: string;
  title: string | null;
  created_at: number; // ms timestamp
}

export interface ProjectItem {
  project_id: string;
  latest_run: LatestRun;
}

export interface ProjectsResponse {
  projects: ProjectItem[];
}

export const getProjects = (limit: number = 10) => {
  return request.get<ProjectsResponse>("/api/projects", {
    params: { limit },
  });
};

export interface ProjectRunsResponse {
  runs: LatestRun[];
}

export const getProjectRuns = (projectId: string, limit: number = 20) => {
  return request.get<ProjectRunsResponse>(`/api/projects/${projectId}/runs`, {
    params: { limit },
  });
};

