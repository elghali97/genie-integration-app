"""Genie Conversational API integration using Databricks SDK."""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.dashboards import GenieMessage

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


def get_workspace_client() -> WorkspaceClient:
    """Get or create a Databricks Workspace Client."""
    try:
        # The SDK will automatically handle authentication from:
        # 1. Environment variables (DATABRICKS_HOST, DATABRICKS_TOKEN)
        # 2. Databricks CLI configuration
        # 3. OAuth for Apps
        w = WorkspaceClient()
        logger.info(f"Workspace client initialized for host: {w.config.host}")
        return w
    except Exception as e:
        logger.error(f"Failed to initialize Workspace Client: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize Databricks connection: {str(e)}"
        )


def process_genie_message(genie_message: GenieMessage, space_id: str) -> ChatResponse:
    """Process a GenieMessage response and extract relevant data."""
    try:
        conversation_id = genie_message.conversation_id
        message_id = genie_message.id
        status = genie_message.status.value if genie_message.status else "UNKNOWN"
        
        logger.info(f"Processing message {message_id} with status: {status}")
        
        # Initialize response data
        sql_query = None
        query_description = None
        query_results = None
        text_content = None
        content = genie_message.content or ""
        
        # Process attachments if present
        if genie_message.attachments:
            w = get_workspace_client()
            
            for attachment in genie_message.attachments:
                # Handle text attachments
                if attachment.text:
                    text_content = attachment.text.content or ""
                    logger.info(f"Found text attachment: {text_content[:100]}...")
                
                # Handle query attachments
                if attachment.query:
                    sql_query = attachment.query.query or ""
                    query_description = attachment.query.description or ""
                    attachment_id = attachment.id
                    
                    logger.info(f"Found query attachment: {query_description[:100]}...")
                    
                    # Fetch query results using SDK
                    if attachment_id:
                        try:
                            result_response = w.genie.get_message_attachment_query_result(
                                space_id=space_id,
                                conversation_id=conversation_id,
                                message_id=message_id,
                                attachment_id=attachment_id
                            )
                            
                            # Extract data from response
                            if result_response.statement_response:
                                statement_response = result_response.statement_response
                                
                                # Get data
                                data_array = []
                                if statement_response.result and statement_response.result.data_array:
                                    data_array = statement_response.result.data_array
                                
                                # Get schema
                                columns = []
                                column_types = []
                                if statement_response.manifest and statement_response.manifest.schema:
                                    schema = statement_response.manifest.schema
                                    if schema.columns:
                                        columns = [col.name for col in schema.columns]
                                        column_types = [col.type_text for col in schema.columns]
                                
                                if columns and data_array:
                                    query_results = {
                                        "columns": columns,
                                        "column_types": column_types,
                                        "data": data_array,
                                        "row_count": len(data_array)
                                    }
                                    logger.info(f"Retrieved query results: {len(data_array)} rows")
                        
                        except Exception as e:
                            logger.warning(f"Failed to fetch query results: {e}")
        
        # Determine response content
        response_content = query_description or text_content or content or "Query completed successfully."
        
        # Map Genie status to our MessageStatus
        if status == "COMPLETED":
            message_status = MessageStatus.COMPLETED
        elif status == "FAILED":
            message_status = MessageStatus.FAILED
        else:
            message_status = MessageStatus.PROCESSING
        
        return ChatResponse(
            conversation_id=conversation_id,
            message_id=message_id,
            content=response_content,
            status=message_status,
            sql_query=sql_query,
            query_results=query_results,
            timestamp=datetime.now()
        )
    
    except Exception as e:
        logger.error(f"Error processing Genie message: {e}")
        raise


@router.post("/send-message", response_model=ChatResponse)
async def send_message(message: ChatMessage):
    """Send a message to Genie and get response using Databricks SDK."""
    
    # Get Genie Space ID
    GENIE_SPACE_ID = os.getenv('DATABRICKS_GENIE_SPACE_ID', '')
    
    if not GENIE_SPACE_ID:
        logger.error("Missing Genie Space ID configuration")
        raise HTTPException(
            status_code=500,
            detail="Genie Space ID not configured. Please set DATABRICKS_GENIE_SPACE_ID."
        )
    
    try:
        # Get Workspace Client
        w = get_workspace_client()
        
        conversation_id = message.conversation_id
        
        # Start new conversation or continue existing one
        if not conversation_id:
            logger.info("Starting new conversation with SDK")
            
            # Use SDK to start conversation and wait for completion
            genie_message = w.genie.start_conversation_and_wait(
                space_id=GENIE_SPACE_ID,
                content=message.content,
                timeout=timedelta(minutes=5)
            )
            
            logger.info(f"Started conversation: {genie_message.conversation_id}, message: {genie_message.id}")
        
        else:
            logger.info(f"Continuing conversation: {conversation_id} with SDK")
            
            # Use SDK to create message and wait for completion
            genie_message = w.genie.create_message_and_wait(
                space_id=GENIE_SPACE_ID,
                conversation_id=conversation_id,
                content=message.content,
                timeout=timedelta(minutes=5)
            )
            
            logger.info(f"Sent message: {genie_message.id}")
        
        # Process the Genie message and return response
        return process_genie_message(genie_message, GENIE_SPACE_ID)
    
    except Exception as e:
        logger.error(f"Error in Genie API: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to communicate with Genie: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Check Genie API configuration using Databricks SDK."""
    try:
        w = get_workspace_client()
        space_id = os.getenv('DATABRICKS_GENIE_SPACE_ID', '')
        
        # Try to get the Genie space to verify configuration
        if space_id:
            try:
                space = w.genie.get_space(space_id=space_id)
                return {
                    "status": "healthy",
                    "configured": True,
                    "space_id": space_id[:8] + "..." if space_id else None,
                    "space_name": space.name if space else None,
                    "host": w.config.host[:30] + "..." if w.config.host else None
                }
            except Exception as e:
                logger.warning(f"Failed to verify Genie space: {e}")
                return {
                    "status": "space_not_accessible",
                    "configured": True,
                    "space_id": space_id[:8] + "..." if space_id else None,
                    "host": w.config.host[:30] + "..." if w.config.host else None,
                    "error": str(e)
                }
        else:
            return {
                "status": "not_configured",
                "configured": False,
                "error": "DATABRICKS_GENIE_SPACE_ID not set"
            }
    except Exception as e:
        return {
            "status": "error",
            "configured": False,
            "error": str(e)
        }