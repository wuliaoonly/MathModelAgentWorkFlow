from fastapi import APIRouter, HTTPException
from pathlib import Path
import json
import re
from app.utils.log_util import logger
from app.config.setting import settings
from app.utils.common_utils import get_config_template
from app.schemas.enums import CompTemplate
from app.services.redis_manager import redis_manager
from app.utils.log_util import logger
from app.db.database import AsyncSessionLocal
from app.db.models import Run
from sqlalchemy import select
from fastapi import Query

router = APIRouter()


@router.get("/")
async def root():
    return {"message": "Hello World"}


@router.get("/config")
async def config():
    return {
        "environment": settings.ENV,
        "deepseek_model": settings.DEEPSEEK_MODEL,
        "deepseek_base_url": settings.DEEPSEEK_BASE_URL,
        "max_chat_turns": settings.MAX_CHAT_TURNS,
        "max_retries": settings.MAX_RETRIES,
        "CORS_ALLOW_ORIGINS": settings.CORS_ALLOW_ORIGINS,
    }


@router.get("/writer_seque")
async def get_writer_seque():
    # 返回论文顺序
    config_template: dict = get_config_template(CompTemplate.CHINA)
    return list(config_template.keys())


@router.get("/track")
async def track(task_id: str):
    # 获取任务的token使用情况

    pass


@router.get("/status")
async def get_service_status():
    """获取各个服务的状态"""
    status = {
        "backend": {"status": "running", "message": "Backend service is running"},
        "redis": {"status": "unknown", "message": "Redis connection status unknown"}
    }

    # 检查Redis连接状态
    try:
        redis_client = await redis_manager.get_client()
        await redis_client.ping()
        status["redis"] = {"status": "running", "message": "Redis connection is healthy"}
    except Exception as e:
        logger.error(f"Redis connection failed: {str(e)}")
        status["redis"] = {"status": "error", "message": f"Redis connection failed: {str(e)}"}

    return status


@router.get("/task/{task_id}/messages")
async def get_task_messages(task_id: str):
    """获取任务的历史消息（用于页面刷新后恢复消息）"""
    try:
        # 检查任务是否存在
        redis_client = await redis_manager.get_client()
        if not await redis_client.exists(f"task_id:{task_id}"):
            raise HTTPException(status_code=404, detail="Task not found")
        
        # 读取消息文件
        messages_file = Path("logs/messages") / f"{task_id}.json"
        
        if not messages_file.exists():
            logger.info(f"任务 {task_id} 的消息文件不存在，返回空列表")
            return {"task_id": task_id, "messages": []}
        
        with open(messages_file, "r", encoding="utf-8") as f:
            messages = json.load(f)
        
        logger.info(f"成功获取任务 {task_id} 的 {len(messages)} 条历史消息")
        return {"task_id": task_id, "messages": messages}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务消息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get task messages: {str(e)}")


@router.get("/tasks")
async def get_tasks_list(limit: int = 50):
    """获取历史任务列表（基于文件系统）"""
    try:
        work_dir = Path("project/work_dir")
        
        if not work_dir.exists():
            logger.warning("工作目录不存在")
            return {"tasks": []}
        
        tasks = []
        
        # 遍历工作目录下的所有任务文件夹
        for task_folder in work_dir.iterdir():
            if task_folder.is_dir() and task_folder.name != ".gitkeep":
                task_id = task_folder.name
                
                # 获取任务信息
                task_info = {
                    "task_id": task_id,
                    "created_at": None,
                    "has_notebook": False,
                    "has_result": False,
                    "title": None
                }
                
                # 检查是否有 notebook.ipynb
                notebook_path = task_folder / "notebook.ipynb"
                if notebook_path.exists():
                    task_info["has_notebook"] = True
                    task_info["created_at"] = notebook_path.stat().st_mtime
                
                # 检查是否有 res.md
                result_path = task_folder / "res.md"
                if result_path.exists():
                    task_info["has_result"] = True
                    if not task_info["created_at"]:
                        task_info["created_at"] = result_path.stat().st_mtime
                    
                    # 尝试从 res.md 中提取标题
                    try:
                        with open(result_path, "r", encoding="utf-8") as f:
                            content = f.read(500)  # 只读取前500字符
                            # 查找第一个 # 标题
                            title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
                            if title_match:
                                task_info["title"] = title_match.group(1).strip()
                    except Exception as e:
                        logger.warning(f"读取任务 {task_id} 标题失败: {str(e)}")
                
                # 如果没有找到创建时间，使用文件夹的创建时间
                if not task_info["created_at"]:
                    task_info["created_at"] = task_folder.stat().st_mtime
                
                # 如果没有标题，使用任务ID作为标题
                if not task_info["title"]:
                    task_info["title"] = f"任务 {task_id[:8]}..."
                
                tasks.append(task_info)
        
        # 按创建时间倒序排序
        tasks.sort(key=lambda x: x["created_at"] or 0, reverse=True)
        
        # 限制返回数量
        tasks = tasks[:limit]
        
        logger.info(f"获取到 {len(tasks)} 个历史任务")
        return {"tasks": tasks}
    
    except Exception as e:
        logger.error(f"获取任务列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get tasks list: {str(e)}")


@router.get("/api/projects")
async def get_projects(limit: int = Query(10, ge=1, le=100)):
    """
    最近项目列表：从 SQLite `runs` 表推导最近一次 run。
    只读接口，最小可用响应用于前端“最近 runs”回放列表。
    """
    try:
        async with AsyncSessionLocal() as session:
            # 取更多 run 后再去重，避免 distinct + 聚合写法带来的复杂度
            stmt = select(Run).order_by(Run.created_at.desc()).limit(limit * 5)
            rows = (await session.execute(stmt)).scalars().all()

        latest_by_project: dict[str, Run] = {}
        for r in rows:
            if r.project_id not in latest_by_project:
                latest_by_project[r.project_id] = r

        projects = [
            {
                "project_id": pid,
                "latest_run": {
                    "run_id": r.run_id,
                    "status": r.status,
                    "title": r.title,
                    "created_at": int(r.created_at.timestamp() * 1000),
                },
            }
            for pid, r in latest_by_project.items()
        ]
        projects.sort(
            key=lambda x: x["latest_run"]["created_at"] or 0, reverse=True
        )
        projects = projects[:limit]
        return {"projects": projects}
    except Exception as e:
        logger.error(f"获取 projects 失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get projects: {str(e)}"
        )


@router.get("/api/projects/{project_id}/runs")
async def get_project_runs(
    project_id: str,
    limit: int = Query(10, ge=1, le=200),
):
    """返回指定 project 的最近 runs（只读 runs 表）"""
    try:
        async with AsyncSessionLocal() as session:
            stmt = (
                select(Run)
                .where(Run.project_id == project_id)
                .order_by(Run.created_at.desc())
                .limit(limit)
            )
            rows = (await session.execute(stmt)).scalars().all()

        runs = [
            {
                "run_id": r.run_id,
                "project_id": r.project_id,
                "status": r.status,
                "title": r.title,
                "created_at": int(r.created_at.timestamp() * 1000),
            }
            for r in rows
        ]
        return {"runs": runs}
    except Exception as e:
        logger.error(f"获取 project runs 失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get project runs: {str(e)}"
        )


@router.get("/task/{task_id}/info")
async def get_task_info(task_id: str):
    """获取单个任务的详细信息"""
    try:
        work_dir = Path("project/work_dir") / task_id
        
        if not work_dir.exists():
            raise HTTPException(status_code=404, detail="Task not found")
        
        task_info = {
            "task_id": task_id,
            "created_at": work_dir.stat().st_mtime,
            "has_notebook": False,
            "has_result": False,
            "has_docx": False,
            "title": None,
            "files": []
        }
        
        # 检查各种文件
        notebook_path = work_dir / "notebook.ipynb"
        if notebook_path.exists():
            task_info["has_notebook"] = True
        
        result_path = work_dir / "res.md"
        if result_path.exists():
            task_info["has_result"] = True
            # 提取标题
            try:
                with open(result_path, "r", encoding="utf-8") as f:
                    content = f.read(500)
                    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
                    if title_match:
                        task_info["title"] = title_match.group(1).strip()
            except Exception as e:
                logger.warning(f"读取任务标题失败: {str(e)}")
        
        docx_path = work_dir / "res.docx"
        if docx_path.exists():
            task_info["has_docx"] = True
        
        # 获取所有文件列表
        for file_path in work_dir.iterdir():
            if file_path.is_file():
                task_info["files"].append({
                    "name": file_path.name,
                    "size": file_path.stat().st_size,
                    "modified_at": file_path.stat().st_mtime
                })
        
        if not task_info["title"]:
            task_info["title"] = f"任务 {task_id[:8]}..."
        
        return task_info
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get task info: {str(e)}")
