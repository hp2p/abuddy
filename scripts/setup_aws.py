#!/usr/bin/env python
"""
AWS 리소스 초기 설정 (최초 1회 실행).
생성: S3 버킷, DynamoDB 테이블 2개, Cognito User Pool, EC2 IAM 역할.

실행 후 출력되는 Cognito 값을 .env 에 복사하세요.
"""
import json
import sys

import boto3
from loguru import logger

sys.path.insert(0, "src")
from abuddy.config import settings

REGION = settings.aws_region


# ── S3 ────────────────────────────────────────────

def create_s3_bucket():
    s3 = boto3.client("s3", region_name=REGION)
    try:
        if REGION == "us-east-1":
            s3.create_bucket(Bucket=settings.s3_bucket)
        else:
            s3.create_bucket(
                Bucket=settings.s3_bucket,
                CreateBucketConfiguration={"LocationConstraint": REGION},
            )
        logger.info(f"Created S3 bucket: {settings.s3_bucket}")
    except s3.exceptions.BucketAlreadyOwnedByYou:
        logger.info(f"S3 bucket already exists: {settings.s3_bucket}")


# ── DynamoDB ──────────────────────────────────────

def create_questions_table():
    ddb = boto3.client("dynamodb", region_name=REGION)
    try:
        ddb.create_table(
            TableName=settings.dynamodb_questions_table,
            KeySchema=[{"AttributeName": "question_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "question_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        logger.info(f"Created table: {settings.dynamodb_questions_table}")
    except ddb.exceptions.ResourceInUseException:
        logger.info(f"Table already exists: {settings.dynamodb_questions_table}")


def create_user_profile_table():
    """PK=user_id — 유저별 스트릭·시험일·오늘 풀이 수"""
    ddb = boto3.client("dynamodb", region_name=REGION)
    try:
        ddb.create_table(
            TableName=settings.dynamodb_user_profile_table,
            KeySchema=[{"AttributeName": "user_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "user_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        logger.info(f"Created table: {settings.dynamodb_user_profile_table}")
    except ddb.exceptions.ResourceInUseException:
        logger.info(f"Table already exists: {settings.dynamodb_user_profile_table}")


def create_user_questions_table():
    """PK=uq_id — 퀴즈 풀이 중 사용자가 남긴 팔로업 질문 수집"""
    ddb = boto3.client("dynamodb", region_name=REGION)
    try:
        ddb.create_table(
            TableName=settings.dynamodb_user_questions_table,
            KeySchema=[{"AttributeName": "uq_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "uq_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        logger.info(f"Created table: {settings.dynamodb_user_questions_table}")
    except ddb.exceptions.ResourceInUseException:
        logger.info(f"Table already exists: {settings.dynamodb_user_questions_table}")


def create_schedule_table():
    """PK=user_id, SK=question_id (멀티유저)"""
    ddb = boto3.client("dynamodb", region_name=REGION)
    try:
        ddb.create_table(
            TableName=settings.dynamodb_schedule_table,
            KeySchema=[
                {"AttributeName": "user_id", "KeyType": "HASH"},
                {"AttributeName": "question_id", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "user_id", "AttributeType": "S"},
                {"AttributeName": "question_id", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        logger.info(f"Created table: {settings.dynamodb_schedule_table}")
    except ddb.exceptions.ResourceInUseException:
        logger.info(f"Table already exists: {settings.dynamodb_schedule_table}")


# ── Cognito ───────────────────────────────────────

def create_cognito_user_pool(app_base_url: str) -> dict:
    """
    Cognito User Pool + App Client 생성.
    Returns: {user_pool_id, client_id, client_secret, domain}
    """
    cognito = boto3.client("cognito-idp", region_name=REGION)
    pool_name = "abuddy-users"

    # User Pool 생성
    try:
        pool = cognito.create_user_pool(
            PoolName=pool_name,
            AutoVerifiedAttributes=["email"],
            UsernameAttributes=["email"],
            Policies={
                "PasswordPolicy": {
                    "MinimumLength": 8,
                    "RequireUppercase": False,
                    "RequireLowercase": True,
                    "RequireNumbers": True,
                    "RequireSymbols": False,
                }
            },
        )
        pool_id = pool["UserPool"]["Id"]
        logger.info(f"Created Cognito User Pool: {pool_id}")
    except cognito.exceptions.InvalidParameterException as e:
        logger.error(f"Failed to create User Pool: {e}")
        raise

    # App Client 생성
    callback_url = f"{app_base_url}/auth/callback"
    logout_url = f"{app_base_url}/auth/login"
    client = cognito.create_user_pool_client(
        UserPoolId=pool_id,
        ClientName="abuddy-web",
        GenerateSecret=True,
        ExplicitAuthFlows=["ALLOW_USER_SRP_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"],
        AllowedOAuthFlows=["code"],
        AllowedOAuthScopes=["openid", "email", "profile"],
        AllowedOAuthFlowsUserPoolClient=True,
        CallbackURLs=[callback_url],
        LogoutURLs=[logout_url],
        SupportedIdentityProviders=["COGNITO"],
    )
    client_id = client["UserPoolClient"]["ClientId"]
    client_secret = client["UserPoolClient"]["ClientSecret"]

    # Cognito Domain 설정 (호스팅 UI용)
    domain_prefix = f"abuddy-{pool_id.split('_')[1].lower()[:10]}"
    try:
        cognito.create_user_pool_domain(UserPoolId=pool_id, Domain=domain_prefix)
        logger.info(f"Created Cognito domain: {domain_prefix}")
    except cognito.exceptions.InvalidParameterException:
        logger.warning("Domain may already exist, continuing...")

    full_domain = f"{domain_prefix}.auth.{REGION}.amazoncognito.com"
    return {
        "user_pool_id": pool_id,
        "client_id": client_id,
        "client_secret": client_secret,
        "domain": full_domain,
    }


# ── IAM ───────────────────────────────────────────

def create_iam_role():
    iam = boto3.client("iam", region_name=REGION)
    role_name = "abuddy-ec2-role"
    trust = json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "ec2.amazonaws.com"},
            "Action": "sts:AssumeRole",
        }],
    })
    try:
        iam.create_role(RoleName=role_name, AssumeRolePolicyDocument=trust)
        for policy in [
            "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess",
            "arn:aws:iam::aws:policy/AmazonS3FullAccess",
            "arn:aws:iam::aws:policy/AmazonBedrockFullAccess",
        ]:
            iam.attach_role_policy(RoleName=role_name, PolicyArn=policy)
        iam.create_instance_profile(InstanceProfileName=role_name)
        iam.add_role_to_instance_profile(InstanceProfileName=role_name, RoleName=role_name)
        logger.info(f"Created IAM role: {role_name}")
    except iam.exceptions.EntityAlreadyExistsException:
        logger.info(f"IAM role already exists: {role_name}")
    except Exception as e:
        if "AccessDenied" in str(e):
            logger.warning(
                "IAM 권한 없음. 다음 중 하나를 선택하세요:\n"
                "  A) IAM Console에서 abuddy-dev 유저에 IAMFullAccess 추가 후 재실행\n"
                "  B) IAM Console에서 직접 생성:\n"
                "     Roles → Create role → EC2 → 정책 3개(DynamoDB/S3/Bedrock) → 이름: abuddy-ec2-role"
            )
        else:
            raise


# ── 메인 ──────────────────────────────────────────

if __name__ == "__main__":
    import sys
    app_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8002"
    logger.info(f"Setting up AWS resources in {REGION} (app_base_url={app_url})")

    create_s3_bucket()
    create_questions_table()
    create_schedule_table()
    create_user_questions_table()
    create_user_profile_table()
    create_iam_role()

    # Cognito는 이미 .env에 설정되어 있으면 재생성 안 함
    if settings.cognito_user_pool_id:
        logger.info("Cognito already configured in .env — skipping pool creation")
        print("\n✅ DynamoDB 테이블/S3/IAM 업데이트 완료. Cognito는 기존 설정 유지.")
        sys.exit(0)

    cognito = create_cognito_user_pool(app_url)

    print("\n" + "=" * 60)
    print("✅ 완료! 아래 값을 .env 에 복사하세요:\n")
    print(f"COGNITO_USER_POOL_ID={cognito['user_pool_id']}")
    print(f"COGNITO_CLIENT_ID={cognito['client_id']}")
    print(f"COGNITO_CLIENT_SECRET={cognito['client_secret']}")
    print(f"COGNITO_DOMAIN={cognito['domain']}")
    print(f"APP_BASE_URL={app_url}")
    print("=" * 60 + "\n")
