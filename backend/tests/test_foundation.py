import json
from pathlib import Path
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from app.main import create_app
from app.settings import PROJECT_ROOT, Settings


def test_health_and_capabilities_match_design(tmp_path):
    settings = Settings(_env_file=None, storage_dir=tmp_path / 'storage', database_url=f'sqlite:///{tmp_path}/app.db')
    client = TestClient(create_app(settings))
    schema = json.loads((PROJECT_ROOT / 'docs/current/contracts/domain.schema.json').read_text())
    for path, name in [('health', 'Health'), ('capabilities', 'Capabilities')]:
        response = client.get('/api/v1/' + path)
        assert response.status_code == 200
        Draft202012Validator({**schema, '$ref': f'#/$defs/{name}'}).validate(response.json())
    caps = client.get('/api/v1/capabilities').json()
    assert caps['storage'] == caps['database'] == 'available'
    assert caps['is_simulated'] is True
    for key in ['parser_pdf', 'ocr', 'word_converter', 'workflow_api']:
        assert caps[key] == 'unavailable'


def test_paths_and_root_env_are_cwd_independent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    settings = Settings(_env_file=None)
    assert settings.storage_dir == PROJECT_ROOT / 'var/storage'
    assert settings.database_url == 'sqlite:///' + str(PROJECT_ROOT / 'var/zhb.db')
    env = tmp_path / 'config.env'
    env.write_text('ZB_AI_PROVIDER=internal_model\nZB_MODEL_API_KEY=private-test-key\n')
    configured = Settings(_env_file=env)
    assert configured.ai_provider == 'internal_model'
    assert 'private-test-key' not in repr(configured)
    assert Settings.model_config['env_file'] == PROJECT_ROOT / '.env'


def test_real_provider_never_falls_back_or_leaks_secrets(tmp_path):
    for provider in ['haier_workflow', 'internal_model']:
        settings = Settings(_env_file=None, ai_provider=provider, workflow_api_key='secret-value', storage_dir=tmp_path, database_url='sqlite:///:memory:')
        response = TestClient(create_app(settings)).get('/api/v1/capabilities')
        assert response.json()['ai_provider'] == provider
        assert response.json()['is_simulated'] is False
        assert response.json()['workflow_api'] == 'unavailable'
        assert 'secret-value' not in response.text


def test_unwritable_storage_and_invalid_db_are_unavailable(tmp_path):
    occupied = tmp_path / 'file'
    occupied.write_text('preserve')
    settings = Settings(_env_file=None, storage_dir=occupied, database_url=f'sqlite:///{occupied}/bad.db')
    client = TestClient(create_app(settings))
    caps = client.get('/api/v1/capabilities').json()
    assert caps['storage'] == caps['database'] == 'unavailable'
    assert client.get('/api/v1/health').json()['status'] == 'ok'
    assert occupied.read_text() == 'preserve'


def test_cors_and_openapi():
    client = TestClient(create_app(Settings(_env_file=None)))
    response = client.options('/api/v1/health', headers={'Origin': 'http://localhost:5173', 'Access-Control-Request-Method': 'GET'})
    assert response.headers['access-control-allow-origin'] == 'http://localhost:5173'
    assert set(client.get('/openapi.json').json()['paths']) == {'/api/v1/health', '/api/v1/capabilities', '/api/v1/projects', '/api/v1/projects/{project_id}', '/api/v1/jobs/{job_id}', '/api/v1/jobs/{job_id}/retry'}
