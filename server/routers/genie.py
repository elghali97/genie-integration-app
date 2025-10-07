"""Genie Conversational API integration."""

import os
import asyncio
import logging
import json
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx
from databricks.sdk import WorkspaceClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


class MessageStatus(str, Enum):
    """Message processing status."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SUBMITTED = "SUBMITTED"


class ChatMessage(BaseModel):
    """Chat message model."""
    content: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat response model."""
    conversation_id: str
    message_id: str
    content: str
    status: MessageStatus
    sql_query: Optional[str] = None
    query_results: Optional[Dict[str, Any]] = None
    timestamp: datetime


def get_auth_config():
    """Get authentication configuration for Databricks."""
    # First try environment variables (works in Databricks Apps)
    host = os.getenv('DATABRICKS_HOST', '').rstrip('/')
    token = os.getenv('DATABRICKS_TOKEN')

    # If not found, try to get from SDK
    if not host or not token:
        try:
            from databricks.sdk import WorkspaceClient
            from databricks.sdk.core import Config

            # Try to get workspace client which will handle auth automatically
            w = WorkspaceClient()
            config = w.config

            # Get host from the SDK config
            if not host:
                host = config.host

            # Get token if we don't have it
            if not token:
                token = config.token
                # In OAuth scenarios, try to get from header factory
                if not token and hasattr(config, '_header_factory'):
                    auth_header = config._header_factory()
                    if auth_header and 'Authorization' in auth_header:
                        token = auth_header['Authorization'].replace('Bearer ', '')

            logger.info(f"Auth via SDK - Host: {host[:30] if host else 'None'}..., Token: {'Present' if token else 'Missing'}")
        except Exception as e:
            logger.warning(f"SDK auth attempt: {e}")

    # Try loading from .env.local as last resort
    if not host or not token:
        try:
            from dotenv import load_dotenv
            load_dotenv('.env.local')
            host = os.getenv('DATABRICKS_HOST', '').rstrip('/')
            token = os.getenv('DATABRICKS_TOKEN')
        except:
            pass

    # Ensure host has proper formatting
    if host:
        host = host.rstrip('/')
        # Ensure host has https:// prefix
        if not host.startswith('http'):
            host = f"https://{host}"

    logger.info(f"Final auth config - Host: {host[:30] if host else 'None'}..., Token: {'Present' if token else 'Missing'}")
    return host, token


@router.post("/send-message", response_model=ChatResponse)
async def send_message(message: ChatMessage):
    """Send a message to Genie and get response."""

    # Get Genie Space ID
    GENIE_SPACE_ID = os.getenv('DATABRICKS_GENIE_SPACE_ID', '')

    if not GENIE_SPACE_ID:
        logger.error("Missing Genie Space ID configuration")
        raise HTTPException(
            status_code=500,
            detail="Genie Space ID not configured. Please set DATABRICKS_GENIE_SPACE_ID."
        )

    # Get authentication
    host, token = get_auth_config()

    if not host or not token:
        logger.error(f"Missing auth - Host: {bool(host)}, Token: {bool(token)}")
        raise HTTPException(
            status_code=500,
            detail="Authentication not configured properly."
        )

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    conversation_id = message.conversation_id

    async with httpx.AsyncClient(timeout=60.0, verify=False) as client:
        try:
            # Start new conversation or continue existing one
            if not conversation_id:
                logger.info("Starting new conversation")
                start_url = f"{host}/api/2.0/genie/spaces/{GENIE_SPACE_ID}/start-conversation"
                payload = {"content": message.content}

                logger.info(f"Calling: {start_url}")
                response = await client.post(start_url, headers=headers, json=payload)

                if response.status_code != 200:
                    logger.error(f"Failed to start conversation: {response.status_code} - {response.text}")
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Failed to start conversation: {response.text}"
                    )

                data = response.json()
                conversation_id = data.get("conversation_id")
                message_id = data.get("message_id")
                logger.info(f"Started conversation: {conversation_id}, message: {message_id}")

            else:
                logger.info(f"Continuing conversation: {conversation_id}")
                send_url = f"{host}/api/2.0/genie/spaces/{GENIE_SPACE_ID}/conversations/{conversation_id}/messages"
                payload = {"content": message.content}

                logger.info(f"Sending message to: {send_url}")
                response = await client.post(send_url, headers=headers, json=payload)

                if response.status_code != 200:
                    logger.error(f"Failed to send message: {response.status_code} - {response.text}")
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Failed to send message: {response.text}"
                    )

                data = response.json()
                message_id = data.get("message_id")
                logger.info(f"Sent message: {message_id}")

            # Poll for completion
            for attempt in range(20):
                await asyncio.sleep(3)

                status_url = f"{host}/api/2.0/genie/spaces/{GENIE_SPACE_ID}/conversations/{conversation_id}/messages/{message_id}"
                logger.info(f"Checking status: attempt {attempt + 1}")

                status_response = await client.get(status_url, headers=headers)

                if status_response.status_code != 200:
                    logger.warning(f"Status check failed: {status_response.status_code}")
                    continue

                status_data = status_response.json()
                message_status = status_data.get("status", "")

                logger.info(f"Message status: {message_status}")

                if message_status == "COMPLETED":
                    # Extract response
                    content = status_data.get("content", "")
                    attachments = status_data.get("attachments", [])

                    sql_query = None
                    query_description = None
                    query_results = None
                    text_content = None

                    # Process attachments
                    for attachment in attachments:
                        # Handle text attachments
                        if "text" in attachment:
                            text_info = attachment.get("text", {})
                            text_content = text_info.get("content", "")

                        # Handle query attachments
                        if "query" in attachment:
                            query_info = attachment.get("query", {})
                            sql_query = query_info.get("query", "")
                            query_description = query_info.get("description", "")
                            attachment_id = attachment.get("attachment_id")

                            # Fetch query results
                            if attachment_id:
                                result_url = f"{status_url}/query-result/{attachment_id}"
                                logger.info(f"Fetching query results from: {result_url}")

                                result_response = await client.get(result_url, headers=headers)

                                if result_response.status_code == 200:
                                    result_data = result_response.json()

                                    # Extract data from response
                                    statement_response = result_data.get("statement_response", {})
                                    result_section = statement_response.get("result", {})
                                    data_array = result_section.get("data_array", [])

                                    manifest = statement_response.get("manifest", {})
                                    schema = manifest.get("schema", {})
                                    columns = schema.get("columns", [])

                                    if columns and data_array:
                                        query_results = {
                                            "columns": [col.get("name") for col in columns],
                                            "column_types": [col.get("type_text") for col in columns],
                                            "data": data_array,
                                            "row_count": len(data_array)
                                        }

                    # Determine response content
                    response_content = query_description or text_content or content or "Query completed successfully."

                    return ChatResponse(
                        conversation_id=conversation_id,
                        message_id=message_id,
                        content=response_content,
                        status=MessageStatus.COMPLETED,
                        sql_query=sql_query,
                        query_results=query_results,
                        timestamp=datetime.now()
                    )

                elif message_status == "FAILED":
                    error_msg = status_data.get("error", "Request failed")
                    logger.error(f"Message failed: {error_msg}")
                    return ChatResponse(
                        conversation_id=conversation_id,
                        message_id=message_id,
                        content=f"Error: {error_msg}",
                        status=MessageStatus.FAILED,
                        timestamp=datetime.now()
                    )

            # Timeout
            return ChatResponse(
                conversation_id=conversation_id,
                message_id=message_id,
                content="Request timed out. Please try again.",
                status=MessageStatus.PROCESSING,
                timestamp=datetime.now()
            )

        except Exception as e:
            logger.error(f"Error in Genie API: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to communicate with Genie: {str(e)}"
            )


@router.get("/health")
async def health_check():
    """Check Genie API configuration."""
    try:
        host, token = get_auth_config()
        configured = bool(os.getenv('DATABRICKS_GENIE_SPACE_ID')) and bool(token) and bool(host)

        return {
            "status": "healthy" if configured else "not_configured",
            "configured": configured,
            "space_id": os.getenv('DATABRICKS_GENIE_SPACE_ID', '')[:8] + "..." if os.getenv('DATABRICKS_GENIE_SPACE_ID') else None,
            "host": host[:30] + "..." if host else None
        }
    except Exception as e:
        return {
            "status": "error",
            "configured": False,
            "error": str(e)
        }