"""FastAPI application for Databricks Genie Integration."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from server.routers import genie


def load_env_file(filepath: str) -> None:
    """Load environment variables from a file."""
    if Path(filepath).exists():
        with open(filepath) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, _, value = line.partition('=')
                    if key and value:
                        os.environ[key] = value


# Load environment files
load_env_file('.env')
load_env_file('.env.local')


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    yield


app = FastAPI(
    title='Genie Integration App',
    description='Databricks App with Genie Conversational API integration',
    version='1.0.0',
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# Include API routers
app.include_router(genie.router, prefix='/api/genie', tags=['genie'])

# Serve static files (React build)
client_path = Path(__file__).parent.parent / 'client' / 'dist'
if client_path.exists():
    app.mount('/assets', StaticFiles(directory=str(client_path / 'assets')), name='assets')

    @app.get('/{path:path}')
    async def serve_spa(path: str):
        """Serve the React SPA for all routes."""
        index_path = client_path / 'index.html'
        if index_path.exists():
            return FileResponse(str(index_path))
        return {"error": "Frontend not built"}