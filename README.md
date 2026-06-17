# G360 AI Backend: Secure Serverless Enterprise Architecture

A production-grade, highly secure, and cost-optimized Generative AI backend built entirely on AWS. This project provisions a private-first serverless architecture using **Terraform** and deploys a **FastAPI** application on **AWS Fargate** to interact with **Amazon Bedrock**.

## 🏗️ Architecture

This project follows a strict "Private-First" methodology. All compute resources are isolated within private subnets, and inbound traffic is strictly routed through an API Gateway via a VPC Link.

```mermaid
flowchart TD
    Client([Internet / Client]) --> API_GW[API Gateway HTTP]
    
    subgraph AWS Cloud [AWS Cloud - us-east-1]
        
        API_GW -->|VPC Link| SD[Cloud Map / Service Discovery]
        
        subgraph VPC [Custom VPC]
            direction TB
            SD --> Fargate[ECS Fargate Task\nFastAPI Application]
            
            subgraph Private Subnets
                Fargate
                RDS[(RDS PostgreSQL\nt4g.micro)]
            end
        end
        
        Fargate -->|IAM Task Role| Bedrock[Amazon Bedrock\nAI Models]
        Fargate -->|IAM Task Role| DynamoDB[(DynamoDB\nNoSQL Store)]
        Fargate -->|IAM Task Role| S3[(Amazon S3\nData Lake)]
        Fargate -->|Execution Role| CW[CloudWatch Logs]
        Fargate -->|Execution Role| ECR[Elastic Container Registry]
    end

    classDef aws fill:#FF9900,stroke:#232F3E,stroke-width:2px,color:black;
    classDef compute fill:#D5E8D4,stroke:#82B366,stroke-width:2px,color:black;
    classDef storage fill:#DAE8FC,stroke:#6C8EBF,stroke-width:2px,color:black;
    
    class API_GW,SD,CW,ECR aws;
    class Fargate compute;
    class Bedrock,RDS,DynamoDB,S3 storage;