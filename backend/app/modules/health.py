from fastapi import APIRouter
from fastapi.responses import JSONResponse
from postgrest.exceptions import APIError

from app.db.supabase import get_supabase

router = APIRouter(tags=['health'])

_CONNECTED_CODES = frozenset({'PGRST205', '42P01'})
_PROBE_TABLE = 'realstick_health_probe'


@router.get('/health')
def health():
    return {'status': 'ok', 'service': 'realstick-api'}


@router.get(
    '/health/database',
    responses={
        200: {'description': 'Supabase database reachable'},
        503: {'description': 'Supabase database unavailable'},
    },
)
def health_database():
    try:
        get_supabase().table(_PROBE_TABLE).select('*').limit(1).execute()
    except APIError as exc:
        if exc.code in _CONNECTED_CODES:
            return {'status': 'ok', 'service': 'realstick-api', 'database': 'connected'}
        return _database_unavailable()
    except Exception:
        return _database_unavailable()

    return {'status': 'ok', 'service': 'realstick-api', 'database': 'connected'}


def _database_unavailable():
    return JSONResponse(
        status_code=503,
        content={
            'status': 'error',
            'service': 'realstick-api',
            'database': 'disconnected',
            'message': 'Unable to connect to the database.',
        },
    )
