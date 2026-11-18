from typing import Annotated
from fastapi import APIRouter, Header
from app.schemas.core import ProjectCreate, ProjectPatch, Project, ProjectList, Job, JobAccepted
from app.services.projects import ProjectService
from app.tasks.store import JobStore

Key = Annotated[str, Header(alias='Idempotency-Key', min_length=1)]
Actor = Annotated[str, Header(alias='X-Actor-Id', min_length=1)]

def router(database, default_actor):
    api = APIRouter()
    projects = ProjectService(database)
    jobs = JobStore(database)

    @api.post('/projects', response_model=Project, status_code=201, operation_id='create_project')
    def create_project(body: ProjectCreate, key: Key, actor: Actor = default_actor):
        return projects.create(body, key, actor)

    @api.get('/projects', response_model=ProjectList, operation_id='list_projects')
    def list_projects():
        return projects.list()

    @api.get('/projects/{project_id}', response_model=Project, operation_id='get_project')
    def get_project(project_id: str):
        return projects.get(project_id)

    @api.patch('/projects/{project_id}', response_model=Project, operation_id='update_project')
    def update_project(project_id: str, body: ProjectPatch, key: Key, actor: Actor = default_actor):
        return projects.patch(project_id, body, key, actor)

    @api.get('/jobs/{job_id}', response_model=Job, operation_id='get_job')
    def get_job(job_id: str):
        return jobs.get(job_id)

    @api.post('/jobs/{job_id}/retry', response_model=JobAccepted, status_code=202, operation_id='retry_job')
    def retry_job(job_id: str, key: Key, actor: Actor = default_actor):
        return jobs.retry(job_id, key, actor)

    return api
