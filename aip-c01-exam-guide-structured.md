# AIP-C01 AWS Certified Generative AI Developer - Professional
# Structured Exam Guide — Seed Data for Concept Graph
# Source: docs.aws.amazon.com/aws-certification/latest/ai-professional-01/ (retrieved 2026-03-28)

---

## EXAM OVERVIEW

- **Exam Code:** AIP-C01
- **Full Title:** AWS Certified Generative AI Developer - Professional
- **Released:** November 2025
- **Questions:** 75 total (65 scored + 10 unscored)
- **Score Range:** 100–1,000 (scaled)
- **Passing Score:** 750
- **Scoring Model:** Compensatory (no per-domain pass requirement)
- **Question Types:** Multiple Choice, Multiple Response

### Target Candidate
- 2+ years building production-grade applications on AWS or open-source technologies
- General AI/ML or data engineering experience
- 1+ year hands-on experience implementing GenAI solutions

### Validated Competencies
- Design and implement solutions using vector stores, RAG, knowledge bases, and GenAI architectures
- Integrate FMs into applications and business workflows
- Apply prompt engineering and management techniques
- Implement agentic AI solutions
- Optimize GenAI applications for cost, performance, and business value
- Implement security, governance, and Responsible AI practices
- Troubleshoot, monitor, and optimize GenAI applications
- Evaluate FMs for quality and responsibility

### Out-of-Scope Job Tasks
- Model development and training
- Advanced ML techniques
- Data engineering and feature engineering

---

## DOMAIN WEIGHTINGS

| Domain | Title                                                              | Weight |
|--------|--------------------------------------------------------------------|--------|
| 1      | Foundation Model Integration, Data Management, and Compliance      | 31%    |
| 2      | Implementation and Integration                                     | 26%    |
| 3      | AI Safety, Security, and Governance                                | 20%    |
| 4      | Operational Efficiency and Optimization for GenAI Applications     | 12%    |
| 5      | Testing, Validation, and Troubleshooting                           | 11%    |

---

## DOMAIN 1: Foundation Model Integration, Data Management, and Compliance
**Source:** https://docs.aws.amazon.com/aws-certification/latest/ai-professional-01/ai-professional-01-domain1.html

---

### Task 1.1: Analyze requirements and design GenAI solutions

#### Skill 1.1.1
Create comprehensive architectural designs that align with specific business needs and technical constraints.
- Using appropriate FMs
- Using appropriate integration patterns
- Using appropriate deployment strategies

#### Skill 1.1.2
Develop technical proof-of-concept implementations to validate feasibility, performance characteristics, and business value before proceeding to full-scale deployment.
- Using Amazon Bedrock

#### Skill 1.1.3
Create standardized technical components to ensure consistent implementation across multiple deployment scenarios.
- Using the AWS Well-Architected Framework
- Using AWS WA Tool Generative AI Lens

---

### Task 1.2: Select and configure FMs

#### Skill 1.2.1
Assess and choose FMs to ensure optimal alignment with specific business use cases and technical requirements.
- Performance benchmarks
- Capability analysis
- Limitation evaluation

#### Skill 1.2.2
Create flexible architecture patterns to enable dynamic model selection and provider switching without requiring code modifications.
- Using AWS Lambda
- Using Amazon API Gateway
- Using AWS AppConfig

#### Skill 1.2.3
Design resilient AI systems to ensure continuous operation during service disruptions.
- Using AWS Step Functions circuit breaker patterns
- Using Amazon Bedrock Cross-Region Inference for models with limited regional availability
- Cross-Region model deployment
- Graceful degradation strategies

#### Skill 1.2.4
Implement FM customization deployment and lifecycle management.
- Using Amazon SageMaker AI to deploy domain-specific fine-tuned models
- Parameter-efficient adaptation techniques such as LoRA and adapters for model deployment
- SageMaker Model Registry for versioning and deploying customized models
- Automated deployment pipelines to update models
- Rollback strategies for failed deployments
- Lifecycle management to retire and replace models

---

### Task 1.3: Implement data validation and processing pipelines for FM consumption

#### Skill 1.3.1
Create comprehensive data validation workflows to ensure data meets quality standards for FM consumption.
- Using AWS Glue Data Quality
- Using SageMaker Data Wrangler
- Using custom Lambda functions
- Using Amazon CloudWatch metrics

#### Skill 1.3.2
Create data processing workflows to handle complex data types including text, image, audio, and tabular data with specialized processing requirements for FM consumption.
- Using Amazon Bedrock multimodal models
- Using SageMaker Processing
- Using AWS Transcribe
- Advanced multimodal pipeline architectures

#### Skill 1.3.3
Format input data for FM inference according to model-specific requirements.
- JSON formatting for Amazon Bedrock API requests
- Structured data preparation for SageMaker AI endpoints
- Conversation formatting for dialog-based applications

#### Skill 1.3.4
Enhance input data quality to improve FM response quality and consistency.
- Using Amazon Bedrock to reformat text
- Using Amazon Comprehend to extract entities
- Using Lambda functions to normalize data

---

### Task 1.4: Design and implement vector store solutions

#### Skill 1.4.1
Create advanced vector database architectures specifically for FM augmentation to enable efficient semantic retrieval beyond traditional search capabilities.
- Using Amazon Bedrock Knowledge Bases for hierarchical organization
- Using Amazon OpenSearch Service with the Neural plugin for Amazon Bedrock integration for topic-based segmentation
- Using Amazon RDS with Amazon S3 document repositories
- Using Amazon DynamoDB with vector databases for metadata and embeddings

#### Skill 1.4.2
Develop comprehensive metadata frameworks to improve search precision and context awareness for FM interactions.
- Using S3 object metadata for document timestamps
- Custom attributes for authorship information
- Tagging systems for domain classification

#### Skill 1.4.3
Implement high-performance vector database architectures to optimize semantic search performance at scale for FM retrieval.
- OpenSearch sharding strategies
- Multi-index approaches for specialized domains
- Hierarchical indexing techniques

#### Skill 1.4.4
Use AWS services to create integration components to connect with resources.
- Document management systems
- Knowledge bases
- Internal wikis for comprehensive data integration in GenAI applications

#### Skill 1.4.5
Design and deploy data maintenance systems to ensure that vector stores contain current and accurate information for FM augmentation.
- Incremental update mechanisms
- Real-time change detection systems
- Automated synchronization workflows
- Scheduled refresh pipelines

---

### Task 1.5: Design retrieval mechanisms for FM augmentation

#### Skill 1.5.1
Develop effective document segmentation approaches to optimize retrieval performance for FM context augmentation.
- Using Amazon Bedrock chunking capabilities
- Using Lambda functions to implement fixed-size chunking
- Custom processing for hierarchical chunking based on content structure

#### Skill 1.5.2
Select and configure optimal embedding solutions to create efficient vector representations for semantic search.
- Using Amazon Titan embeddings based on dimensionality and domain fit
- Evaluating performance characteristics of Amazon Bedrock embedding models
- Using Lambda functions to batch generate embeddings

#### Skill 1.5.3
Deploy and configure vector search solutions to enable semantic search capabilities for FM augmentation.
- Using OpenSearch Service with vector search capabilities
- Using Amazon Aurora with the pgvector extension
- Using Amazon Bedrock Knowledge Bases with managed vector store functionality

#### Skill 1.5.4
Create advanced search architectures to improve the relevance and accuracy of retrieved information for FM context.
- Using OpenSearch for semantic search
- Hybrid search that combines keywords and vectors
- Using Amazon Bedrock reranker models

#### Skill 1.5.5
Develop sophisticated query handling systems to improve retrieval effectiveness and result quality for FM augmentation.
- Using Amazon Bedrock for query expansion
- Using Lambda functions for query decomposition
- Using Step Functions for query transformation

#### Skill 1.5.6
Create consistent access mechanisms to enable seamless integration with FMs.
- Function calling interfaces for vector search
- Model Context Protocol (MCP) clients for vector queries
- Standardized API patterns for retrieval augmentation

---

### Task 1.6: Implement prompt engineering strategies and governance for FM interactions

#### Skill 1.6.1
Create effective model instruction frameworks to control FM behavior and outputs.
- Using Amazon Bedrock Prompt Management to enforce role definitions
- Using Amazon Bedrock Guardrails to enforce responsible AI guidelines
- Template configurations to format responses

#### Skill 1.6.2
Build interactive AI systems to maintain context and improve user interactions with FMs.
- Using Step Functions for clarification workflows
- Using Amazon Comprehend for intent recognition
- Using DynamoDB for conversation history storage

#### Skill 1.6.3
Implement comprehensive prompt management and governance systems to ensure consistency and oversight of FM operations.
- Using Amazon Bedrock Prompt Management to create parameterized templates and approval workflows
- Using Amazon S3 to store template repositories
- Using AWS CloudTrail to track usage
- Using Amazon CloudWatch Logs to log access

#### Skill 1.6.4
Develop quality assurance systems to ensure prompt effectiveness and reliability for FMs.
- Using Lambda functions to verify expected output
- Using Step Functions to test edge cases
- Using CloudWatch to test prompt regression

#### Skill 1.6.5
Enhance FM performance to refine prompts iteratively and improve response quality beyond basic prompting techniques.
- Structured input components
- Output format specifications
- Chain-of-thought instruction patterns
- Feedback loops

#### Skill 1.6.6
Design complex prompt systems to handle sophisticated tasks with FMs.
- Using Amazon Bedrock Prompt Flows for sequential prompt chains
- Conditional branching based on model responses
- Reusable prompt components
- Integrated pre-processing and post-processing steps

---

## DOMAIN 2: Implementation and Integration
**Source:** https://docs.aws.amazon.com/aws-certification/latest/ai-professional-01/ai-professional-01-domain2.html

---

### Task 2.1: Implement agentic AI solutions and tool integrations

#### Skill 2.1.1
Develop intelligent autonomous systems with appropriate memory and state management capabilities.
- Using Strands Agents and AWS Agent Squad for multi-agent systems
- Using MCP for agent-tool interactions

#### Skill 2.1.2
Create advanced problem-solving systems to give FMs the ability to break down and solve complex problems by following structured reasoning steps.
- Using Step Functions to implement ReAct patterns
- Using chain-of-thought reasoning approaches

#### Skill 2.1.3
Develop safeguarded AI workflows to ensure controlled FM behavior.
- Using Step Functions to implement stopping conditions
- Using Lambda functions to implement timeout mechanisms
- Using IAM policies to enforce resource boundaries
- Using circuit breakers to mitigate failures

#### Skill 2.1.4
Create sophisticated model coordination systems to optimize performance across multiple capabilities.
- Using specialized FMs to perform complex tasks
- Using custom aggregation logic for model ensembles
- Using model selection frameworks

#### Skill 2.1.5
Develop collaborative AI systems to enhance FM capabilities with human expertise.
- Using Step Functions to orchestrate review and approval processes
- Using API Gateway to implement feedback collection mechanisms
- Using human augmentation patterns

#### Skill 2.1.6
Implement intelligent tool integrations to extend FM capabilities and to ensure reliable tool operations.
- Using the Strands API to implement custom behaviors
- Using standardized function definitions
- Using Lambda functions to implement error handling and parameter validation

#### Skill 2.1.7
Develop model extension frameworks to enhance FM capabilities.
- Using Lambda functions to implement stateless MCP servers that provide lightweight tool access
- Using Amazon ECS to implement MCP servers that provide complex tools
- Using MCP client libraries to ensure consistent access patterns

---

### Task 2.2: Implement model deployment strategies

#### Skill 2.2.1
Deploy FMs based on specific application needs and performance requirements.
- Using Lambda functions for on-demand invocation
- Using Amazon Bedrock provisioned throughput configurations
- Using SageMaker AI endpoints to implement hybrid solutions

#### Skill 2.2.2
Deploy FM solutions by addressing unique challenges of LLMs that differ from traditional ML deployments.
- Implementing container-based deployment patterns optimized for memory requirements
- Implementing container-based deployment patterns optimized for GPU utilization
- Implementing container-based deployment patterns optimized for token processing capacity
- Following specialized model loading strategies

#### Skill 2.2.3
Develop optimized FM deployment approaches to balance performance and resource requirements for GenAI workloads.
- Selecting appropriate models
- Using smaller pre-trained models for specific tasks
- Using API-based model cascading to perform routine queries

---

### Task 2.3: Design and implement enterprise integration architectures

#### Skill 2.3.1
Create enterprise connectivity solutions to seamlessly incorporate FM capabilities into existing enterprise environments.
- Using API-based integrations with legacy systems
- Using event-driven architectures to implement loose coupling
- Using data synchronization patterns

#### Skill 2.3.2
Develop integrated AI capabilities to enhance existing applications with GenAI functionality.
- Using API Gateway to implement microservice integrations
- Using Lambda functions for webhook handlers
- Using Amazon EventBridge to implement event-driven integrations

#### Skill 2.3.3
Create secure access frameworks to ensure appropriate security controls.
- Using identity federation between FM services and enterprise systems
- Using role-based access control for model and data access
- Using least privilege API access to FMs

#### Skill 2.3.4
Develop cross-environment AI solutions to ensure data compliance across jurisdictions while enabling FM access.
- Using AWS Outposts for on-premises data integration
- Using AWS Wavelength to perform edge deployments
- Using secure routing between cloud and on-premises resources

#### Skill 2.3.5
Implement CI/CD pipelines and GenAI gateway architectures to implement secure and compliant consumption patterns in enterprise environments.
- Using AWS CodePipeline
- Using AWS CodeBuild
- Using automated testing frameworks for continuous deployment and testing of GenAI components with security scans and rollback support
- Using centralized abstraction layers
- Using observability and control mechanisms

---

### Task 2.4: Implement FM API integrations

#### Skill 2.4.1
Create flexible model interaction systems.
- Using Amazon Bedrock APIs to manage synchronous requests from various compute environments
- Using language-specific AWS SDKs and Amazon SQS for asynchronous processing
- Using API Gateway to provide custom API clients with request validation

#### Skill 2.4.2
Develop real-time AI interaction systems to provide immediate feedback from FM.
- Using Amazon Bedrock streaming APIs for incremental response delivery
- Using WebSockets or server-sent events to generate text in real time
- Using API Gateway to implement chunked transfer encoding

#### Skill 2.4.3
Create resilient FM systems to ensure reliable operations.
- Using the AWS SDK for exponential backoff
- Using API Gateway to manage rate limiting
- Using fallback mechanisms for graceful degradation
- Using AWS X-Ray to provide observability across service boundaries

#### Skill 2.4.4
Develop intelligent model routing systems to optimize model selection.
- Using application code to implement static routing configurations
- Using Step Functions for dynamic content-based routing to specialized FMs
- Using intelligent model routing based on metrics
- Using API Gateway with request transformations for routing logic

---

### Task 2.5: Implement application integration patterns and development tools

#### Skill 2.5.1
Create FM API interfaces to address the specific requirements of GenAI workloads.
- Using API Gateway to handle streaming responses
- Token limit management
- Retry strategies to handle model timeouts

#### Skill 2.5.2
Develop accessible AI interfaces to accelerate adoption and integration of FMs.
- Using AWS Amplify to develop declarative UI components
- Using OpenAPI specifications for API-first development approaches
- Using Amazon Bedrock Prompt Flows for no-code workflow builders

#### Skill 2.5.3
Create business system enhancements.
- Using Lambda functions to implement CRM enhancements
- Using Step Functions to orchestrate document processing systems
- Using Amazon Q Business data sources to provide internal knowledge tools
- Using Amazon Bedrock Data Automation to manage automated data processing workflows

#### Skill 2.5.4
Enhance developer productivity to accelerate development workflows for GenAI applications.
- Using Amazon Q Developer to generate and refactor code
- Using code suggestions for API assistance
- Using AI component testing
- Using performance optimization

#### Skill 2.5.5
Develop advanced GenAI applications to implement sophisticated AI capabilities.
- Using Strands Agents and AWS Agent Squad for AWS native orchestration
- Using Step Functions to orchestrate agent design patterns
- Using Amazon Bedrock to manage prompt chaining patterns

#### Skill 2.5.6
Improve troubleshooting efficiency for FM applications.
- Using CloudWatch Logs Insights to analyze prompts and responses
- Using X-Ray to trace FM API calls
- Using Amazon Q Developer to implement GenAI-specific error pattern recognition

---

## DOMAIN 3: AI Safety, Security, and Governance
**Source:** https://docs.aws.amazon.com/aws-certification/latest/ai-professional-01/ai-professional-01-domain3.html

---

### Task 3.1: Implement input and output safety controls

#### Skill 3.1.1
Develop comprehensive content safety systems to protect against harmful user inputs to FMs.
- Use Amazon Bedrock guardrails to filter content
- Use Step Functions and Lambda functions to implement custom moderation workflows
- Implement real-time validation mechanisms

#### Skill 3.1.2
Create content safety frameworks to prevent harmful outputs.
- Use Amazon Bedrock guardrails to filter responses
- Use specialized FM evaluations for content moderation and toxicity detection
- Use text-to-SQL transformations to ensure deterministic results

#### Skill 3.1.3
Develop accuracy verification systems to reduce hallucinations in FM responses.
- Use Amazon Bedrock Knowledge Base to ground responses and perform fact-checking
- Use confidence scoring and semantic similarity search for verification
- Use JSON Schema to enforce structured outputs

#### Skill 3.1.4
Create defense-in-depth safety systems to provide comprehensive protection against FM misuse.
- Use Amazon Comprehend to develop pre-processing filters
- Use Amazon Bedrock to implement model-based guardrails
- Use Lambda functions to perform post-processing validation
- Use API Gateway to implement API response filtering

#### Skill 3.1.5
Implement advanced threat detection to protect against adversarial inputs and security vulnerabilities.
- Implement prompt injection and jailbreak detection mechanisms
- Implement input sanitization and content filters
- Implement safety classifiers
- Implement automated adversarial testing workflows

---

### Task 3.2: Implement data security and privacy controls

#### Skill 3.2.1
Develop protected AI environments to ensure comprehensive security for FM deployments.
- Use VPC endpoints to isolate networks
- Use IAM policies to enforce secure data access patterns
- Use AWS Lake Formation to provide granular data access
- Use CloudWatch to monitor data access

#### Skill 3.2.2
Develop privacy-preserving systems to protect sensitive information during FM interactions.
- Use Amazon Comprehend and Amazon Macie to detect PII
- Use Amazon Bedrock native data privacy features
- Use Amazon Bedrock guardrails to filter outputs
- Use Amazon S3 Lifecycle configurations to implement data retention policies

#### Skill 3.2.3
Create privacy-focused AI systems to protect user privacy while maintaining FM utility and effectiveness.
- Use data masking techniques
- Use Amazon Comprehend PII detection
- Use anonymization strategies for sensitive information
- Use Amazon Bedrock guardrails

---

### Task 3.3: Implement AI governance and compliance mechanisms

#### Skill 3.3.1
Develop compliance frameworks to ensure regulatory compliance for FM deployments.
- Use SageMaker AI to develop programmatic model cards
- Use AWS Glue to automatically track data lineage
- Use metadata tagging for systematic data source attribution
- Use CloudWatch Logs to collect comprehensive decision logs

#### Skill 3.3.2
Implement data source tracking to maintain traceability in GenAI applications.
- Use AWS Glue Data Catalog to register data sources
- Use metadata tagging for source attribution in FM-generated content
- Use CloudTrail for audit logging

#### Skill 3.3.3
Create organizational governance systems to ensure consistent oversight of FM implementations.
- Develop comprehensive frameworks that align with organizational policies
- Align with regulatory requirements
- Align with responsible AI principles

#### Skill 3.3.4
Implement continuous monitoring and advanced governance controls to support safety audits and regulatory readiness.
- Use automated detection for misuse, drift, and policy violations
- Use bias drift monitoring
- Use automated alerting and remediation workflows
- Use token-level redaction
- Use response logging
- Use AI output policy filters

---

### Task 3.4: Implement responsible AI principles

#### Skill 3.4.1
Develop transparent AI systems in FM outputs.
- Use reasoning displays to provide user-facing explanations
- Use CloudWatch to collect confidence metrics and quantify uncertainty
- Use evidence presentation for source attribution
- Use Amazon Bedrock agent tracing to provide reasoning traces

#### Skill 3.4.2
Apply fairness evaluations to ensure unbiased FM outputs.
- Use pre-defined fairness metrics in CloudWatch
- Use Amazon Bedrock Prompt Management and Amazon Bedrock Prompt Flows to perform systematic A/B testing
- Use Amazon Bedrock with LLM-as-a-judge solutions to perform automated model evaluations

#### Skill 3.4.3
Develop policy-compliant AI systems to ensure adherence to responsible AI practices.
- Use Amazon Bedrock guardrails based on policy requirements
- Use model cards to document FM limitations
- Use Lambda functions to perform automated compliance checks

---

## DOMAIN 4: Operational Efficiency and Optimization for GenAI Applications
**Source:** https://docs.aws.amazon.com/aws-certification/latest/ai-professional-01/ai-professional-01-domain4.html

---

### Task 4.1: Implement cost optimization and resource efficiency strategies

#### Skill 4.1.1
Develop token efficiency systems to reduce FM costs while maintaining effectiveness.
- Token estimation and tracking
- Context window optimization
- Response size controls
- Prompt compression
- Context pruning
- Response limiting

#### Skill 4.1.2
Create cost-effective model selection frameworks.
- Cost-capability tradeoff evaluation
- Tiered FM usage based on query complexity
- Inference cost balancing against response quality
- Price-to-performance ratio measurement
- Efficient inference patterns

#### Skill 4.1.3
Develop high-performance FM systems to maximize resource utilization and throughput for GenAI workloads.
- Batching strategies
- Capacity planning
- Utilization monitoring
- Auto-scaling configurations
- Provisioned throughput optimization

#### Skill 4.1.4
Create intelligent caching systems to reduce costs and improve response times by avoiding unnecessary FM invocations.
- Semantic caching
- Result fingerprinting
- Edge caching
- Deterministic request hashing
- Prompt caching

---

### Task 4.2: Optimize application performance

#### Skill 4.2.1
Create responsive AI systems to address latency-cost tradeoffs and improve the user experience with FMs.
- Pre-computation to perform predictable queries
- Latency-optimized Amazon Bedrock models for time-sensitive applications
- Parallel requests for complex workflows
- Response streaming
- Performance benchmarking

#### Skill 4.2.2
Enhance retrieval performance to improve the relevance and speed of retrieved information for FM context augmentation.
- Index optimization
- Query preprocessing
- Hybrid search implementation with custom scoring

#### Skill 4.2.3
Implement FM throughput optimization to address the specific throughput challenges of GenAI workloads.
- Token processing optimization
- Batch inference strategies
- Concurrent model invocation management

#### Skill 4.2.4
Enhance FM performance to achieve optimal results for specific GenAI use cases.
- Model-specific parameter configurations
- A/B testing to evaluate improvements
- Appropriate temperature and top-k/top-p selection based on requirements

#### Skill 4.2.5
Create efficient resource allocation systems specifically for FM workloads.
- Capacity planning for token processing requirements
- Utilization monitoring for prompt and completion patterns
- Auto-scaling configurations optimized for GenAI traffic patterns

#### Skill 4.2.6
Optimize FM system performance for GenAI workflows.
- API call profiling for prompt-completion patterns
- Vector database query optimization for retrieval augmentation
- Latency reduction techniques specific to LLM inference
- Efficient service communication patterns

---

### Task 4.3: Implement monitoring systems for GenAI applications

#### Skill 4.3.1
Create holistic observability systems to provide complete visibility into FM application performance.
- Operational metrics
- Performance tracing
- FM interaction tracing
- Business impact metrics with custom dashboards

#### Skill 4.3.2
Implement comprehensive GenAI monitoring systems to proactively identify issues and evaluate key performance indicators specific to FM implementations.
- CloudWatch to track token usage
- Prompt effectiveness monitoring
- Hallucination rates tracking
- Response quality monitoring
- Anomaly detection for token burst patterns and response drift
- Amazon Bedrock Model Invocation Logs for detailed request and response analysis
- Performance benchmarks
- Cost anomaly detection

#### Skill 4.3.3
Develop integrated observability solutions to provide actionable insights for FM applications.
- Operational metric dashboards
- Business impact visualizations
- Compliance monitoring
- Forensic traceability and audit logging
- User interaction tracking
- Model behavior pattern tracking

#### Skill 4.3.4
Create tool performance frameworks to ensure optimal tool operation and utilization for FMs.
- Call pattern tracking
- Performance metric collection
- Tool calling observability and multi-agent coordination tracking
- Usage baselines for anomaly detection

#### Skill 4.3.5
Create vector store operational management systems to ensure optimal vector store operation and reliability for FM augmentation.
- Performance monitoring for vector databases
- Automated index optimization routines
- Data quality validation processes

#### Skill 4.3.6
Develop FM-specific troubleshooting frameworks to identify unique GenAI failure modes that are not present in traditional ML systems.
- Golden datasets to detect hallucinations
- Output diffing techniques to conduct response consistency analysis
- Reasoning path tracing to identify logical errors
- Specialized observability pipelines

---

## DOMAIN 5: Testing, Validation, and Troubleshooting
**Source:** https://docs.aws.amazon.com/aws-certification/latest/ai-professional-01/ai-professional-01-domain5.html

---

### Task 5.1: Implement evaluation systems for GenAI

#### Skill 5.1.1
Develop comprehensive assessment frameworks to evaluate the quality and effectiveness of FM outputs beyond traditional ML evaluation approaches.
- Metrics for relevance
- Factual accuracy
- Consistency
- Fluency

#### Skill 5.1.2
Create systematic model evaluation systems to identify optimal configurations.
- Using Amazon Bedrock Model Evaluations
- A/B testing and canary testing of FMs
- Multi-model evaluation
- Cost-performance analysis to measure token efficiency
- Latency-to-quality ratios
- Business outcomes measurement

#### Skill 5.1.3
Develop user-centered evaluation mechanisms to continuously improve FM performance based on user experience.
- Feedback interfaces
- Rating systems for model outputs
- Annotation workflows to assess response quality

#### Skill 5.1.4
Create systematic quality assurance processes to maintain consistent performance standards for FMs.
- Continuous evaluation workflows
- Regression testing for model outputs
- Automated quality gates for deployments

#### Skill 5.1.5
Develop comprehensive assessment systems to ensure thorough evaluation from multiple perspectives for FM outputs.
- RAG evaluation
- Automated quality assessment with LLM-as-a-Judge techniques
- Human feedback collection interfaces

#### Skill 5.1.6
Implement retrieval quality testing to evaluate and optimize information retrieval components for FM augmentation.
- Relevance scoring
- Context matching verification
- Retrieval latency measurements

#### Skill 5.1.7
Develop agent performance frameworks to ensure that agents perform tasks correctly and efficiently.
- Task completion rate measurements
- Tool usage effectiveness evaluations
- Amazon Bedrock Agent evaluations
- Reasoning quality assessment in multi-step workflows

#### Skill 5.1.8
Create comprehensive reporting systems to communicate performance metrics and insights effectively to stakeholders.
- Visualization tools
- Automated reporting mechanisms
- Model comparison visualizations

#### Skill 5.1.9
Create deployment validation systems to maintain reliability during FM updates.
- Synthetic user workflows
- AI-specific output validation for hallucination rates and semantic drift
- Automated quality checks to ensure response consistency

---

### Task 5.2: Troubleshoot GenAI applications

#### Skill 5.2.1
Resolve content handling issues to ensure that necessary information is processed completely in FM interactions.
- Context window overflow diagnostics
- Dynamic chunking strategies
- Prompt design optimization
- Truncation-related error analysis

#### Skill 5.2.2
Diagnose and resolve FM integration issues to identify and fix API integration problems specific to GenAI services.
- Error logging
- Request validation
- Response analysis

#### Skill 5.2.3
Troubleshoot prompt engineering problems to improve FM response quality and consistency beyond basic prompt adjustments.
- Prompt testing frameworks
- Version comparison
- Systematic refinement

#### Skill 5.2.4
Troubleshoot retrieval system issues to identify and resolve problems that affect information retrieval effectiveness for FM augmentation.
- Model response relevance analysis
- Embedding quality diagnostics
- Drift monitoring
- Vectorization issue resolution
- Chunking and preprocessing remediation
- Vector search performance optimization

#### Skill 5.2.5
Troubleshoot prompt maintenance issues to continuously improve the performance of FM interactions.
- Using template testing and CloudWatch Logs to diagnose prompt confusion
- Using X-Ray to implement prompt observability pipelines
- Using schema validation to detect format inconsistencies
- Systematic prompt refinement workflows

---

## APPENDIX A: Technologies and Concepts
**Source:** https://docs.aws.amazon.com/aws-certification/latest/ai-professional-01/ai-professional-01-technologies-concepts.html

Technologies and concepts that might appear on the exam (non-exhaustive):

### GenAI / AI/ML Core
- Retrieval Augmented Generation (RAG)
- Vector databases and embeddings
- Prompt engineering and management
- Foundation model (FM) integration
- Agentic AI systems
- Responsible AI practices
- Content safety and moderation
- Model evaluation and validation

### Operational
- Cost optimization for AI workloads
- Performance tuning for AI applications
- Monitoring and observability for AI systems
- Security and governance for AI applications

### Architecture and Integration
- API design and integration patterns
- Event-driven architectures
- Serverless computing
- Container orchestration
- Infrastructure as code (IaC)
- CI/CD for AI applications
- Hybrid cloud architectures
- Enterprise system integration

---

## APPENDIX B: In-Scope AWS Services and Features
**Source:** https://docs.aws.amazon.com/aws-certification/latest/ai-professional-01/aip-01-in-scope-services.html

### Analytics
- Amazon Athena
- Amazon EMR
- AWS Glue
- Amazon Kinesis
- Amazon OpenSearch Service
- Amazon QuickSight
- Amazon Managed Streaming for Apache Kafka (Amazon MSK)

### Application Integration
- Amazon AppFlow
- AWS AppConfig
- Amazon EventBridge
- Amazon SNS
- Amazon SQS
- AWS Step Functions

### Compute
- AWS App Runner
- Amazon EC2
- AWS Lambda
- AWS Lambda@Edge
- AWS Outposts
- AWS Wavelength

### Containers
- Amazon ECR
- Amazon ECS
- Amazon EKS
- AWS Fargate

### Customer Engagement
- Amazon Connect

### Database
- Amazon Aurora
- Amazon DocumentDB
- Amazon DynamoDB
- Amazon DynamoDB Streams
- Amazon ElastiCache
- Amazon Neptune
- Amazon RDS

### Developer Tools
- AWS Amplify
- AWS CDK
- AWS CLI
- AWS CloudFormation
- AWS CodeArtifact
- AWS CodeBuild
- AWS CodeDeploy
- AWS CodePipeline
- AWS Tools and SDKs
- AWS X-Ray

### Machine Learning
- Amazon Augmented AI
- Amazon Bedrock
- Amazon Bedrock AgentCore
- Amazon Bedrock Knowledge Bases
- Amazon Bedrock Prompt Management
- Amazon Bedrock Prompt Flows
- Amazon Comprehend
- Amazon Kendra
- Amazon Lex
- Amazon Q Business
- Amazon Q Business Apps
- Amazon Q Developer
- Amazon Rekognition
- Amazon SageMaker AI
- Amazon SageMaker Clarify
- Amazon SageMaker Data Wrangler
- Amazon SageMaker Ground Truth
- Amazon SageMaker JumpStart
- Amazon SageMaker Model Monitor
- Amazon SageMaker Model Registry
- Amazon SageMaker Neo
- Amazon SageMaker Processing
- Amazon SageMaker Unified Studio
- Amazon Textract
- Amazon Titan
- Amazon Transcribe

### Management and Governance
- AWS Auto Scaling
- AWS Chatbot
- AWS CloudTrail
- Amazon CloudWatch
- Amazon CloudWatch Logs
- Amazon CloudWatch Synthetics
- AWS Cost Anomaly Detection
- AWS Cost Explorer
- Amazon Managed Grafana
- AWS Service Catalog
- AWS Systems Manager
- AWS Well-Architected Tool

### Migration and Transfer
- AWS DataSync
- AWS Transfer Family

### Networking and Content Delivery
- Amazon API Gateway
- AWS AppSync
- Amazon CloudFront
- Elastic Load Balancing (ELB)
- AWS Global Accelerator
- AWS PrivateLink
- Amazon Route 53
- Amazon VPC

### Security, Identity, and Compliance
- Amazon Cognito
- AWS Encryption SDK
- IAM
- IAM Access Analyzer
- IAM Identity Center
- AWS KMS
- Amazon Macie
- AWS Secrets Manager
- AWS WAF

### Storage
- Amazon EBS
- Amazon EFS
- Amazon S3
- Amazon S3 Intelligent-Tiering
- Amazon S3 Lifecycle policies
- Amazon S3 Cross-Region Replication

---

## APPENDIX C: Community and Third-Party Resources

### GitHub Study Notes
- **Repository:** https://github.com/MakendranG/aws-genai-professional-certification-notes
  - 43 pages of handwritten study notes (JPG images)
  - Created by an Early Adopter badge winner (first 5,000 globally)
  - Preparation used: 24h Udemy course, 35+ h AWS Skill Builder, 375+ practice questions, hands-on labs

### Tutorials Dojo Resources
- **Exam Guide & Topics List:** https://tutorialsdojo.com/aws-certified-generative-ai-developer-professional-certification-aip-c01-exam-guide-and-aip-c01-exam-topics-list/
- **Study Path:** https://tutorialsdojo.com/aws-certified-generative-ai-developer-professional-study-path-aip-c01-exam-guide/
- **Practice Exams (paid):** https://portal.tutorialsdojo.com/courses/aws-certified-generative-ai-developer-professional-aip-c01-practice-exams/
- **Study Guide eBook (paid, 300+ pages):** https://portal.tutorialsdojo.com/product/study-guide-ebook-aws-certified-generative-ai-developer-professional-aip-c01/
- **Video Course (paid):** https://portal.tutorialsdojo.com/courses/aws-certified-generative-ai-developer-professional-aip-c01-video-course/

### AWS Skill Builder
- **Category page (requires JS):** https://skillbuilder.aws/category/exam-prep/generative-ai-developer-professional-aip-c01
- **Exam Prep Plan:** https://skillbuilder.aws/learning-plan/9VXVGYT38G/exam-prep-plan-aws-certified-generative-ai-developer--professional-aipc01--english/4SCMN2659K
- **Official Practice Questions:** https://skillbuilder.aws/learn/HSEKTD11NX/official-practice-question-set-aws-certified--generative-ai-developer--professional-aipc01--english/ZDANP82P4V
- **Domain 1 Practice:** https://skillbuilder.aws/learn/V5N6SFRR6S/domain-1-practice-aws-certified-generative-ai-developer--professional-aipc01-english/NRSMYNRGY3

### Official AWS Exam Landing Page
- https://aws.amazon.com/certification/certified-generative-ai-developer-professional/

### Other
- **Amazon book (350 scenario-based questions):** https://www.amazon.com/AWS-Certified-Generative-Developer-Scenario-Based/dp/B0GBW9FJC7
- **Udemy course:** https://www.udemy.com/course/aws-certified-generative-ai-developer-professional-aip-c01/
- **Sundog Education (Frank Kane):** https://www.sundog-education.com/2025/12/01/new-aws-certified-genai-developer-pro-prep-resources/
