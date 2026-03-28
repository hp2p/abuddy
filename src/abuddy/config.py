from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    aws_region: str = "ap-northeast-2"
    s3_bucket: str = "abuddy-data"
    dynamodb_questions_table: str = "abuddy-questions"
    dynamodb_schedule_table: str = "abuddy-schedule"

    # Haiku: 일상 작업 (문제 출제, 답변 평가, 팔로업)
    bedrock_model_id: str = "global.anthropic.claude-haiku-4-5-20251001-v1:0"
    # Sonnet: 개념 추출, 최초 그래프 생성 (1회성 heavy 작업)
    bedrock_smart_model_id: str = "global.anthropic.claude-sonnet-4-6"

    # Cognito
    cognito_user_pool_id: str = ""
    cognito_client_id: str = ""
    cognito_client_secret: str = ""
    cognito_domain: str = ""        # e.g. "abuddy.auth.ap-northeast-2.amazoncognito.com"
    app_base_url: str = "http://localhost:8000"  # EC2에서는 http://YOUR_EC2_IP

    app_host: str = "0.0.0.0"
    app_port: int = 8002


settings = Settings()
