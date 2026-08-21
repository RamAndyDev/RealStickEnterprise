from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.modules import audits, auth, employee_sessions, franchises, gallery, health, orders, pos, products, public, reports, users
from app.modules.settings import owner_router as owner_settings_router
from app.modules.settings import router as admin_settings_router

settings = get_settings()

app = FastAPI(title='RealStick Enterprise API', version='0.1.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(franchises.router, prefix=settings.api_prefix)
app.include_router(products.router, prefix=settings.api_prefix)
app.include_router(products.owner_router, prefix=settings.api_prefix)
app.include_router(users.admin_router, prefix=settings.api_prefix)
app.include_router(users.owner_router, prefix=settings.api_prefix)
app.include_router(employee_sessions.owner_router, prefix=settings.api_prefix)
app.include_router(admin_settings_router, prefix=settings.api_prefix)
app.include_router(owner_settings_router, prefix=settings.api_prefix)
app.include_router(pos.router, prefix=settings.api_prefix)
app.include_router(orders.router, prefix=settings.api_prefix)
app.include_router(reports.router, prefix=settings.api_prefix)
app.include_router(audits.router, prefix=settings.api_prefix)
app.include_router(public.router, prefix=settings.api_prefix)
app.include_router(gallery.admin_router, prefix=settings.api_prefix)
app.include_router(gallery.public_router, prefix=settings.api_prefix)
