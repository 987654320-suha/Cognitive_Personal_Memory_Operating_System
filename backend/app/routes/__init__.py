# ðŸ“ LOCATION: backend/app/routes/__init__.py
from app.routes.memory_routes         import router as memory_router
from app.routes.search_routes         import router as search_router
from app.routes.upload_routes         import router as upload_router
from app.routes.chat_routes           import router as chat_router
from app.routes.goal_routes           import router as goal_router
from app.routes.stats_routes          import router as stats_router
from app.routes.timeline_routes       import router as timeline_router
from app.routes.pdf_routes            import router as pdf_router
from app.routes.memory_details_routes import router as memory_details_router
from app.routes.index_routes          import router as index_router
from app.routes.watcher_routes        import router as watcher_router
from app.routes.import_routes         import router as import_router
from app.routes.graph_routes          import router as graph_router

all_routers = [
    memory_router, search_router, upload_router, chat_router,
    goal_router, stats_router, timeline_router, pdf_router,
    memory_details_router, index_router, watcher_router,
    import_router, graph_router,
]


