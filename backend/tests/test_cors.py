import re

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from app.main import (
    VERCEL_PREVIEW_ORIGIN_REGEX,
    app,
    cors_allowed_origins,
)


PREVIEW_ORIGIN = 'https://real-stick-enterprise-nuxh4p99v-ram-team5.vercel.app'
PRODUCTION_ORIGIN = 'https://real-stick-enterprise-one.vercel.app'
UNRELATED_ORIGIN = 'https://unrelated-project-ram-team5.vercel.app'


def test_cors_allows_current_vercel_preview_origin():
    with TestClient(app) as client:
        response = client.get('/api/v1/health', headers={'Origin': PREVIEW_ORIGIN})

    assert response.headers['access-control-allow-origin'] == PREVIEW_ORIGIN
    assert response.headers['access-control-allow-credentials'] == 'true'


def test_cors_preserves_configured_production_and_development_origins():
    configured_origins = ['http://localhost:5173', PRODUCTION_ORIGIN]

    assert cors_allowed_origins(configured_origins) == [
        *configured_origins,
        PREVIEW_ORIGIN,
    ]


def test_cors_preview_regex_is_project_and_team_scoped():
    assert re.fullmatch(VERCEL_PREVIEW_ORIGIN_REGEX, PREVIEW_ORIGIN)
    assert not re.fullmatch(VERCEL_PREVIEW_ORIGIN_REGEX, UNRELATED_ORIGIN)
    assert not re.fullmatch(
        VERCEL_PREVIEW_ORIGIN_REGEX,
        'https://real-stick-enterprise-abc-other-team.vercel.app',
    )


def test_cors_rejects_unrelated_vercel_project():
    with TestClient(app) as client:
        response = client.get('/api/v1/health', headers={'Origin': UNRELATED_ORIGIN})

    assert 'access-control-allow-origin' not in response.headers


def test_cors_preflight_allows_preview_login_post():
    with TestClient(app) as client:
        response = client.options(
            '/api/v1/auth/login',
            headers={
                'Origin': PREVIEW_ORIGIN,
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'content-type,authorization',
            },
        )

    assert response.status_code == 200
    assert response.headers['access-control-allow-origin'] == PREVIEW_ORIGIN
    assert response.headers['access-control-allow-credentials'] == 'true'
    assert 'POST' in response.headers['access-control-allow-methods']
    assert response.headers['access-control-allow-headers']
