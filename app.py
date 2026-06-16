import os
import json
import boto3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="g360 Demo Backend")

region = os.getenv("AWS_REGION", "us-east-1")
bedrock = boto3.client(service_name="bedrock-runtime", region_name=region)

# Claude 3 Haiku is Anthropic's most cost-effective and fastest model on Bedrock.
# It costs fractions of a cent per request, perfect for a low-cost demo.
MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"

class PromptRequest(BaseModel):
    prompt: str

@app.get("/health")
def health_check():
    return {"status": "healthy", "layer": "private-subnet"}

@app.post("/api/generate")
def generate_ai_response(request: PromptRequest):
    """
    This endpoint receives a prompt and sends it to Amazon Bedrock.
    """
    # 1. Format the payload specifically for Anthropic Claude 3
    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        # Reduced max_tokens to 100 to strictly limit AWS output charges during the demo
        "max_tokens": 100,
        "messages": [{"role": "user", "content": [{"type": "text", "text": request.prompt}]}]
    }
    
    try:
        # 2. Invoke the Bedrock API
        response = bedrock.invoke_model(
            modelId=MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload)
        )
        
        # 3. Parse the response and return it to the user
        response_body = json.loads(response.get("body").read())
        return {
            "source": "AWS Fargate (Private)",
            "ai_response": response_body["content"][0]["text"]
        }
    except Exception as e:
        # If Bedrock fails (e.g., rate limits, bad IAM permissions), return a 500 error
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)