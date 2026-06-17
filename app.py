from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import boto3
import json
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Initialize AWS Bedrock client
try:
    bedrock = boto3.client(service_name="bedrock-runtime", region_name="us-east-1")
    logger.info("Successfully initialized Bedrock client")
except Exception as e:
    logger.error(f"Failed to initialize Bedrock client: {str(e)}")
    raise

class PromptRequest(BaseModel):
    prompt: str

@app.get("/health")
async def health_check():
    return {"status": "healthy", "layer": "private-subnet"}

@app.post("/api/generate")
async def generate_text(request: PromptRequest):
    try:
        # Matches the model_id specified in your terraform locals
        model_id = "anthropic.claude-3-haiku-20240307-v1:0"

        # Claude 3 uses the Messages API structure
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 512,
            "temperature": 0.7,
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": request.prompt}]
                }
            ]
        })

        response = bedrock.invoke_model(
            modelId=model_id,
            body=body,
            accept="application/json",
            contentType="application/json"
        )
        
        response_body = json.loads(response.get('body').read())
        
        # Parse the Claude 3 response structure
        output_text = response_body.get('content')[0].get('text')

        return {
            "source": "AWS Fargate via Claude 3 Haiku",
            "ai_response": output_text
        }

    except Exception as e:
        logger.error(f"Bedrock invocation error: {str(e)}")
        # Returning a 500 status on error is best practice for