from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    aws_region: str = "ap-northeast-2"
    s3_bucket: str = "abuddy-data"
    dynamodb_questions_table: str = "abuddy-questions"
    dynamodb_schedule_table: str = "abuddy-schedule"
    dynamodb_user_questions_table: str = "abuddy-user-questions"
    dynamodb_user_profile_table: str = "abuddy-user-profile"

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

    # Tavily: AWS 문서 수집 (fetch_concept_docs.py)
    tavily_api_key: str = ""

    # 활성 자격증 (데이터 격리 키: S3 경로, 문제 필터링)
    # 예: "aip-c01" | "CCA"
    active_exam: str = "CCA"

    # TTS (edge-tts)
    tts_voice_ko_female: str = "ko-KR-SunHiNeural"
    tts_voice_ko_male: str = "ko-KR-InJoonNeural"
    tts_voice_en_female: str = "en-US-AriaNeural"
    tts_voice_en_male: str = "en-US-GuyNeural"
    tts_s3_prefix: str = "tts/"

    app_host: str = "0.0.0.0"
    app_port: int = 8002


settings = Settings()
