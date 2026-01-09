"""
FastAPI service for local LLM inference using HuggingFace transformers.
Provides basic authentication and a simple query endpoint.
"""

import os
import secrets
import logging
import traceback
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


# Global model storage
model_cache = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the model on startup and clean up on shutdown."""
    logger.info("Loading model...")

    model_name = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-0.5B")
    device = "cuda" if torch.cuda.is_available() else "cpu"

    logger.info(f"Using model: {model_name}")
    logger.info(f"Using device: {device}")

    # Load tokenizer and model
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        low_cpu_mem_usage=True,
    )
    model.to(device)

    # Create text generation pipeline
    # Note: Don't pass device parameter since we already moved model to device
    text_generator = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
    )

    model_cache["generator"] = text_generator
    model_cache["model_name"] = model_name

    logger.info("Model loaded successfully!")

    yield

    # Cleanup
    logger.info("Shutting down and cleaning up...")
    model_cache.clear()


app = FastAPI(
    title="Local LLM Service",
    description="FastAPI service for local LLM inference",
    version="1.0.0",
    lifespan=lifespan,
)

security = HTTPBasic()


def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify basic authentication credentials."""
    username = os.getenv("LLM_USERNAME", "admin")
    password = os.getenv("LLM_PASSWORD", "password")

    correct_username = secrets.compare_digest(credentials.username, username)
    correct_password = secrets.compare_digest(credentials.password, password)

    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username


class QueryRequest(BaseModel):
    """Request model for LLM queries."""
    prompt: str = Field(..., description="The prompt to send to the LLM")
    max_tokens: Optional[int] = Field(512, description="Maximum number of tokens to generate")
    temperature: Optional[float] = Field(0.7, description="Sampling temperature (0.0-2.0)")
    top_p: Optional[float] = Field(0.95, description="Nucleus sampling parameter")

    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "What is the capital of France?",
                "max_tokens": 100,
                "temperature": 0.7,
                "top_p": 0.95,
            }
        }


class QueryResponse(BaseModel):
    """Response model for LLM queries."""
    response: str = Field(..., description="The generated text from the LLM")
    model_name: str = Field(..., description="The name of the model used")
    prompt: str = Field(..., description="The original prompt")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "Local LLM Service",
        "model": model_cache.get("model_name", "not loaded"),
    }


@app.get("/health")
async def health():
    """Health check endpoint with model status."""
    model_loaded = "generator" in model_cache
    return {
        "status": "healthy" if model_loaded else "unhealthy",
        "model_loaded": model_loaded,
        "model_name": model_cache.get("model_name", "none"),
    }


@app.post("/query", response_model=QueryResponse)
async def query_llm(
    request: QueryRequest,
    username: str = Depends(verify_credentials),
):
    """
    Query the local LLM with a prompt.

    Requires basic authentication.
    """
    logger.info(f"Received query request from user: {username}")
    logger.info(f"Prompt length: {len(request.prompt)} characters")
    logger.info(f"Max tokens: {request.max_tokens}, Temperature: {request.temperature}, Top-p: {request.top_p}")
    logger.debug(f"Prompt preview: {request.prompt[:200]}...")

    generator = model_cache.get("generator")
    if not generator:
        logger.error("Model not loaded!")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not loaded",
        )

    try:
        # Generate response with specified parameters
        logger.info("Generating response...")
        logger.debug(f"Parameters: max_tokens={request.max_tokens}, temp={request.temperature}, top_p={request.top_p}")

        result = generator(
            request.prompt,
            max_new_tokens=request.max_tokens,
            do_sample=True,
            temperature=request.temperature,
            top_p=request.top_p,
        )

        logger.debug(f"Generation complete. Result type: {type(result)}")

        # Extract generated text
        generated_text = result[0]["generated_text"]
        logger.debug(f"Generated text length: {len(generated_text)} characters")

        # Remove the prompt from the response if it's included
        if generated_text.startswith(request.prompt):
            generated_text = generated_text[len(request.prompt):].strip()
            logger.debug("Removed prompt from response")

        logger.info(f"Successfully generated response ({len(generated_text)} chars)")
        logger.debug(f"Response preview: {generated_text[:200]}...")

        return QueryResponse(
            response=generated_text,
            model_name=model_cache["model_name"],
            prompt=request.prompt,
        )

    except Exception as e:
        logger.error(f"Error generating response: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Full traceback:\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating response: {str(e)}",
        )


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
