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
        logger.info(f"Received prompt: {request.prompt}")
        
        # The new Amazon Nova Micro Model ID
        model_id = "amazon.nova-micro-v1:0"

        # The new syntax required for Nova models
        body = json.dumps({
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": request.prompt}]
                }
            ],
            "schemaVersion": "messages-v1"
        })

        logger.info("Sending request to Bedrock Nova Micro...")
        
        response = bedrock.invoke_model(
            modelId=model_id,
            body=body,
            accept="application/json",
            contentType="application/json"
        )
        
        response_body = json.loads(response.get('body').read())
        logger.info("Successfully received response from Bedrock")
        
        # Parse the Nova response structure
        output_text = response_body.get('output', {}).get('message', {}).get('content', [{}])[0].get('text', 'No response generated')

        return {
            "source": "AWS Fargate (Private) via Nova Micro",
            "ai_response": output_text
        }

    except Exception as e:
        logger.error(f"Error during Bedrock invocation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))