#!/usr/bin/env python
"""
Lambda 배포 스크립트 (최초 생성 + 이후 업데이트 모두 처리).

실행:
  uv run scripts/deploy_lambda.py

최초 실행 시:
  - ECR 레포 생성
  - Lambda용 IAM 역할 생성
  - Docker 이미지 빌드 & ECR 푸시
  - Lambda 함수 생성
  - Function URL 생성

이후 실행 시:
  - 이미지 재빌드 & 푸시
  - Lambda 코드/환경변수 업데이트
"""
import json
import os
import subprocess
import sys
import time

import boto3
from botocore.exceptions import ClientError
from loguru import logger

sys.path.insert(0, "src")
from abuddy.config import settings

REGION = settings.aws_region
FUNCTION_NAME = "abuddy"
REPO_NAME = "abuddy"
ROLE_NAME = "abuddy-lambda-role"
MEMORY_MB = 512
TIMEOUT_SEC = 60

# Lambda에 전달할 환경변수 키 목록 (.env에서 읽음)
ENV_KEYS = [
    "COGNITO_USER_POOL_ID",
    "COGNITO_CLIENT_ID",
    "COGNITO_CLIENT_SECRET",
    "COGNITO_DOMAIN",
    "APP_BASE_URL",
    "TAVILY_API_KEY",
]


def get_account_id() -> str:
    return boto3.client("sts", region_name=REGION).get_caller_identity()["Account"]


def ensure_ecr_repo(account_id: str) -> str:
    ecr = boto3.client("ecr", region_name=REGION)
    try:
        ecr.describe_repositories(repositoryNames=[REPO_NAME])
        logger.info(f"ECR repo exists: {REPO_NAME}")
    except ecr.exceptions.RepositoryNotFoundException:
        ecr.create_repository(repositoryName=REPO_NAME)
        logger.info(f"Created ECR repo: {REPO_NAME}")
    return f"{account_id}.dkr.ecr.{REGION}.amazonaws.com/{REPO_NAME}:latest"


def ensure_iam_role(account_id: str) -> str:
    iam = boto3.client("iam")
    try:
        role = iam.get_role(RoleName=ROLE_NAME)
        logger.info(f"IAM role exists: {ROLE_NAME}")
        return role["Role"]["Arn"]
    except iam.exceptions.NoSuchEntityException:
        trust = json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }],
        })
        role = iam.create_role(RoleName=ROLE_NAME, AssumeRolePolicyDocument=trust)
        role_arn = role["Role"]["Arn"]
        for policy in [
            "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
            "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess",
            "arn:aws:iam::aws:policy/AmazonS3FullAccess",
            "arn:aws:iam::aws:policy/AmazonBedrockFullAccess",
        ]:
            iam.attach_role_policy(RoleName=ROLE_NAME, PolicyArn=policy)
        logger.info(f"Created IAM role: {ROLE_NAME} — IAM 전파 대기 중 (10초)")
        time.sleep(10)
        return role_arn


def build_and_push(image_uri: str, account_id: str) -> None:
    registry = f"{account_id}.dkr.ecr.{REGION}.amazonaws.com"
    subprocess.run(
        f"aws ecr get-login-password --region {REGION} | "
        f"docker login --username AWS --password-stdin {registry}",
        shell=True, check=True,
    )
    subprocess.run([
        "docker", "buildx", "build",
        "--platform", "linux/amd64",
        "--provenance=false",
        "--load",
        "-f", "Dockerfile.lambda",
        "-t", f"{REPO_NAME}:latest",
        ".",
    ], check=True)
    subprocess.run(["docker", "tag", f"{REPO_NAME}:latest", image_uri], check=True)
    subprocess.run(["docker", "push", image_uri], check=True)
    logger.info(f"Pushed: {image_uri}")


def load_env_vars() -> dict[str, str]:
    env: dict[str, str] = {}
    if os.path.exists(".env"):
        with open(".env") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    if k in ENV_KEYS:
                        env[k] = v.strip()
    return env


def ensure_lambda(image_uri: str, role_arn: str, env_vars: dict[str, str]) -> None:
    lam = boto3.client("lambda", region_name=REGION)
    env = {"Variables": env_vars}
    try:
        lam.get_function(FunctionName=FUNCTION_NAME)
        # 업데이트
        lam.update_function_code(FunctionName=FUNCTION_NAME, ImageUri=image_uri)
        # 코드 업데이트 완료 대기
        waiter = lam.get_waiter("function_updated")
        waiter.wait(FunctionName=FUNCTION_NAME)
        lam.update_function_configuration(
            FunctionName=FUNCTION_NAME,
            Environment=env,
            Timeout=TIMEOUT_SEC,
            MemorySize=MEMORY_MB,
        )
        logger.info(f"Updated Lambda: {FUNCTION_NAME}")
    except ClientError as e:
        if e.response["Error"]["Code"] != "ResourceNotFoundException":
            raise
        # 최초 생성
        lam.create_function(
            FunctionName=FUNCTION_NAME,
            PackageType="Image",
            Code={"ImageUri": image_uri},
            Role=role_arn,
            Timeout=TIMEOUT_SEC,
            MemorySize=MEMORY_MB,
            Environment=env,
        )
        waiter = lam.get_waiter("function_active")
        waiter.wait(FunctionName=FUNCTION_NAME)
        logger.info(f"Created Lambda: {FUNCTION_NAME}")


def ensure_function_url() -> str:
    lam = boto3.client("lambda", region_name=REGION)
    try:
        resp = lam.get_function_url_config(FunctionName=FUNCTION_NAME)
        url = resp["FunctionUrl"]
        logger.info(f"Function URL exists: {url}")
        return url
    except ClientError as e:
        if e.response["Error"]["Code"] != "ResourceNotFoundException":
            raise
        resp = lam.create_function_url_config(
            FunctionName=FUNCTION_NAME,
            AuthType="NONE",
        )
        url = resp["FunctionUrl"]
        # 공개 접근 허용
        lam.add_permission(
            FunctionName=FUNCTION_NAME,
            StatementId="FunctionURLAllowPublicAccess",
            Action="lambda:InvokeFunctionUrl",
            Principal="*",
            FunctionUrlAuthType="NONE",
        )
        logger.info(f"Created Function URL: {url}")
        return url


if __name__ == "__main__":
    account_id = get_account_id()
    image_uri = ensure_ecr_repo(account_id)
    role_arn = ensure_iam_role(account_id)
    build_and_push(image_uri, account_id)

    env_vars = load_env_vars()
    ensure_lambda(image_uri, role_arn, env_vars)

    url = ensure_function_url()
    base_url = url.rstrip("/")

    print("\n" + "=" * 60)
    print("✅ Lambda 배포 완료!")
    print(f"\nFunction URL: {url}")
    print("\n다음 단계:")
    print(f"1. .env 에서 APP_BASE_URL={base_url} 으로 수정")
    print(f"2. Cognito Callback URL 업데이트:")
    print(f"   uv run scripts/setup_aws.py {base_url}")
    print("=" * 60 + "\n")
