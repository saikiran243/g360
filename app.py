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
        model_id = "amazon.nova-micro-v1:0"

        # Using the standard Bedrock Converse API format
        body = json.dumps({
            "inputText": request.prompt,
            "textGenerationConfig": {
                "maxTokenCount": 512,
                "stopSequences": [],
                "temperature": 0.7,
                "topP": 0.9
            }
        })

        response = bedrock.invoke_model(
            modelId=model_id,
            body=body,
            accept="application/json",
            contentType="application/json"
        )
        
        response_body = json.loads(response.get('body').read())
        
        # Amazon Titan/Nova standard response parsing
        output_text = response_body.get('results')[0].get('outputText')

        return {
            "source": "AWS Fargate (Private) via Nova",
            "ai_response": output_text
        }

    except Exception as e:
        # RETURN THE EXACT ERROR TO THE BROWSER/TERMINAL
        return {
            "error_type": "AWS_BEDROCK_FAILURE",
            "exact_error_message": str(e)
        }