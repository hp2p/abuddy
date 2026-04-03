#!/usr/bin/env python
"""
CloudFront 배포 생성 스크립트.

실행:
  uv run scripts/setup_cloudfront.py

수행 내용:
  - CloudFront distribution 생성 (origin: Lambda Function URL)
  - Cognito Callback/Logout URL을 CloudFront URL로 업데이트
  - .env의 APP_BASE_URL 업데이트 안내
"""
import sys
import time

import boto3
from botocore.exceptions import ClientError
from loguru import logger

sys.path.insert(0, "src")
from abuddy.config import settings

LAMBDA_FUNCTION_NAME = "abuddy"
REGION = settings.aws_region


def get_lambda_function_url() -> str:
    lam = boto3.client("lambda", region_name=REGION)
    resp = lam.get_function_url_config(FunctionName=LAMBDA_FUNCTION_NAME)
    url = resp["FunctionUrl"]
    # CloudFront origin은 프로토콜/trailing slash 제거
    return url.replace("https://", "").rstrip("/")


def find_existing_distribution(origin_domain: str) -> dict | None:
    cf = boto3.client("cloudfront")
    paginator = cf.get_paginator("list_distributions")
    for page in paginator.paginate():
        items = page.get("DistributionList", {}).get("Items", [])
        for dist in items:
            for origin in dist.get("Origins", {}).get("Items", []):
                if origin["DomainName"] == origin_domain:
                    return dist
    return None


def create_distribution(origin_domain: str) -> tuple[str, str]:
    """CloudFront distribution 생성. (distribution_id, domain_name) 반환."""
    cf = boto3.client("cloudfront")

    existing = find_existing_distribution(origin_domain)
    if existing:
        domain = existing["DomainName"]
        dist_id = existing["Id"]
        logger.info(f"CloudFront distribution already exists: https://{domain}")
        return dist_id, domain

    resp = cf.create_distribution(
        DistributionConfig={
            "CallerReference": f"abuddy-{int(time.time())}",
            "Comment": "abuddy Lambda Function URL",
            "Enabled": True,
            "DefaultCacheBehavior": {
                "TargetOriginId": "lambda-origin",
                "ViewerProtocolPolicy": "redirect-to-https",
                "CachePolicyId": "4135ea2d-6df8-44a3-9df3-4b5a84be39ad",        # CachingDisabled
                "OriginRequestPolicyId": "b689b0a8-53d0-40ab-baf2-68738e2966ac", # AllViewer
                "AllowedMethods": {
                    "Quantity": 7,
                    "Items": ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"],
                    "CachedMethods": {
                        "Quantity": 2,
                        "Items": ["GET", "HEAD"],
                    },
                },
                "Compress": True,
            },
            "Origins": {
                "Quantity": 1,
                "Items": [{
                    "Id": "lambda-origin",
                    "DomainName": origin_domain,
                    "CustomOriginConfig": {
                        "HTTPPort": 80,
                        "HTTPSPort": 443,
                        "OriginProtocolPolicy": "https-only",
                        "OriginSslProtocols": {
                            "Quantity": 1,
                            "Items": ["TLSv1.2"],
                        },
                    },
                }],
            },
            "HttpVersion": "http2",
            "PriceClass": "PriceClass_100",  # 미국/유럽/아시아 (저렴한 등급)
        }
    )
    dist = resp["Distribution"]
    dist_id = dist["Id"]
    domain = dist["DomainName"]
    logger.info(f"Created CloudFront distribution: https://{domain} (배포까지 약 5~10분 소요)")
    return dist_id, domain


def update_cognito_callback(cloudfront_url: str) -> None:
    cognito = boto3.client("cognito-idp", region_name=REGION)
    pool_id = settings.cognito_user_pool_id
    client_id = settings.cognito_client_id

    if not pool_id or not client_id:
        logger.warning("Cognito 설정이 .env에 없습니다. 수동으로 업데이트해 주세요.")
        return

    cognito.update_user_pool_client(
        UserPoolId=pool_id,
        ClientId=client_id,
        CallbackURLs=[f"{cloudfront_url}/auth/callback"],
        LogoutURLs=[f"{cloudfront_url}/auth/login"],
        SupportedIdentityProviders=["COGNITO"],
        AllowedOAuthFlows=["code"],
        AllowedOAuthScopes=["openid", "email", "profile"],
        AllowedOAuthFlowsUserPoolClient=True,
    )
    logger.info(f"Cognito Callback URL 업데이트 완료: {cloudfront_url}/auth/callback")


if __name__ == "__main__":
    origin_domain = get_lambda_function_url()
    logger.info(f"Lambda origin: {origin_domain}")

    dist_id, cf_domain = create_distribution(origin_domain)
    cloudfront_url = f"https://{cf_domain}"

    update_cognito_callback(cloudfront_url)

    print("\n" + "=" * 60)
    print("✅ CloudFront 설정 완료!")
    print(f"\nCloudFront URL: {cloudfront_url}")
    print("\n다음 단계:")
    print(f"1. .env 에서 APP_BASE_URL={cloudfront_url} 으로 수정")
    print(f"2. Lambda 환경변수 업데이트:")
    print(f"   uv run scripts/deploy_lambda.py")
    print("=" * 60 + "\n")
