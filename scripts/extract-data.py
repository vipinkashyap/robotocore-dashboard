#!/usr/bin/env python3
"""Extract robotocore AWS service coverage data for the dashboard.

Clones the robotocore repo, runs the parity report generator,
transforms the output, and writes data/coverage.json + site/data/coverage.json.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROBOTOCORE_REPO = "https://github.com/robotocore/robotocore.git"
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# AWS service category mapping
SERVICE_CATEGORIES = {
    # Compute
    "ec2": "Compute", "lambda": "Compute", "batch": "Compute",
    "elasticbeanstalk": "Compute", "autoscaling": "Compute",
    "lightsail": "Compute", "imagebuilder": "Compute",
    "application-autoscaling": "Compute", "compute-optimizer": "Compute",
    # Containers
    "ecs": "Containers", "ecr": "Containers", "eks": "Containers",
    # Storage
    "s3": "Storage", "s3control": "Storage", "s3tables": "Storage",
    "s3vectors": "Storage", "efs": "Storage", "fsx": "Storage",
    "glacier": "Storage", "ebs": "Storage", "backup": "Storage",
    "datasync": "Storage", "storagegateway": "Storage",
    # Database
    "dynamodb": "Database", "dynamodbstreams": "Database",
    "rds": "Database", "rds-data": "Database", "rdsdata": "Database",
    "redshift": "Database", "redshift-data": "Database", "redshiftdata": "Database",
    "elasticache": "Database", "dax": "Database", "memorydb": "Database",
    "dsql": "Database", "neptune": "Database", "docdb": "Database",
    "timestream-write": "Database", "timestream-query": "Database",
    "timestreamwrite": "Database", "timestreamquery": "Database",
    "lakeformation": "Database", "keyspaces": "Database",
    # Networking
    "elb": "Networking", "elbv2": "Networking",
    "route53": "Networking", "route53resolver": "Networking",
    "route53domains": "Networking", "cloudfront": "Networking",
    "vpclattice": "Networking", "directconnect": "Networking",
    "networkfirewall": "Networking", "networkmanager": "Networking",
    "appmesh": "Networking", "globalaccelerator": "Networking",
    "servicediscovery": "Networking",
    # App Integration
    "sqs": "App Integration", "sns": "App Integration",
    "events": "App Integration", "stepfunctions": "App Integration",
    "pipes": "App Integration", "scheduler": "App Integration",
    "mq": "App Integration", "kafka": "App Integration",
    "kinesis": "App Integration", "firehose": "App Integration",
    "kinesisanalyticsv2": "App Integration", "kinesisvideo": "App Integration",
    "datapipeline": "App Integration", "connect": "App Integration",
    "swf": "App Integration", "mwaa": "App Integration",
    "schemas": "App Integration", "appflow": "App Integration",
    # Security
    "iam": "Security", "sts": "Security", "kms": "Security",
    "cognito-idp": "Security", "cognitoidentity": "Security",
    "cognito-identity": "Security",
    "secretsmanager": "Security", "ssoadmin": "Security",
    "sso-admin": "Security", "sso": "Security",
    "shield": "Security", "wafv2": "Security", "waf": "Security",
    "waf-regional": "Security", "guardduty": "Security",
    "securityhub": "Security", "inspector2": "Security",
    "identitystore": "Security", "macie2": "Security",
    "acm": "Security", "acm-pca": "Security", "acmpca": "Security",
    "cloudhsmv2": "Security", "signer": "Security", "ram": "Security",
    "detective": "Security", "accessanalyzer": "Security",
    # Management
    "cloudwatch": "Management", "logs": "Management",
    "cloudformation": "Management", "config": "Management",
    "cloudtrail": "Management", "ssm": "Management",
    "organizations": "Management", "support": "Management",
    "servicecatalog": "Management", "servicecatalogappregistry": "Management",
    "service-quotas": "Management", "resiliencehub": "Management",
    "resource-groups": "Management", "resourcegroupstaggingapi": "Management",
    "account": "Management", "health": "Management",
    "controltower": "Management", "ce": "Management",
    "budgets": "Management", "cur": "Management",
    "pricing": "Management", "wellarchitected": "Management",
    # AI/ML
    "sagemaker": "AI/ML", "sagemaker-runtime": "AI/ML",
    "bedrock": "AI/ML", "bedrock-runtime": "AI/ML",
    "bedrock-agent": "AI/ML", "bedrock-agent-runtime": "AI/ML",
    "bedrockagent": "AI/ML",
    "rekognition": "AI/ML", "textract": "AI/ML",
    "comprehend": "AI/ML", "transcribe": "AI/ML",
    "polly": "AI/ML", "lexv2-models": "AI/ML",
    "personalize": "AI/ML", "forecast": "AI/ML",
    "translate": "AI/ML",
    # Developer Tools
    "codebuild": "Developer Tools", "codecommit": "Developer Tools",
    "codedeploy": "Developer Tools", "codepipeline": "Developer Tools",
    "xray": "Developer Tools", "synthetics": "Developer Tools",
    "appsync": "Developer Tools",
    "apigateway": "Developer Tools", "apigatewayv2": "Developer Tools",
    "apigatewaymanagementapi": "Developer Tools",
    "amplify": "Developer Tools", "codeartifact": "Developer Tools",
    "codestar-connections": "Developer Tools",
    # IoT
    "iot": "IoT", "iot-data": "IoT", "iotdata": "IoT",
    "greengrass": "IoT", "greengrassv2": "IoT",
    # Media
    "medialive": "Media", "mediaconnect": "Media",
    "mediapackage": "Media", "mediapackagev2": "Media",
    "mediastore": "Media", "mediastore-data": "Media",
    "ivs": "Media", "panorama": "Media",
    "kinesis-video-archived-media": "Media",
    # Analytics
    "athena": "Analytics", "glue": "Analytics",
    "emr": "Analytics", "emr-containers": "Analytics",
    "emr-serverless": "Analytics", "emrcontainers": "Analytics",
    "emrserverless": "Analytics",
    "quicksight": "Analytics", "databrew": "Analytics",
    "opensearch": "Analytics", "opensearchserverless": "Analytics",
    "es": "Analytics", "osis": "Analytics",
    # Monitoring
    "xray": "Monitoring",
    # Messaging
    "ses": "Messaging", "sesv2": "Messaging", "pinpoint": "Messaging",
}


def get_category(service_name: str) -> str:
    return SERVICE_CATEGORIES.get(service_name, "Other")


def clone_repo(dest: str) -> str:
    """Clone robotocore repo and return the clone directory path."""
    clone_dir = os.path.join(dest, "robotocore")
    print(f"Cloning robotocore to {clone_dir}...")
    subprocess.run(
        ["git", "clone", "--depth", "1", ROBOTOCORE_REPO, clone_dir],
        check=True,
        capture_output=True,
        text=True,
    )
    return clone_dir


def get_version(clone_dir: str) -> str:
    """Get the latest tag or commit SHA from the cloned repo."""
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=clone_dir,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    # Fallback to commit SHA
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=clone_dir,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def run_parity_report(clone_dir: str, output_path: str) -> dict:
    """Run the parity report generator and return the JSON data."""
    print("Installing dependencies with uv sync...")
    subprocess.run(
        ["uv", "sync"],
        cwd=clone_dir,
        check=True,
        capture_output=True,
        text=True,
    )
    print("Running parity report...")
    subprocess.run(
        ["uv", "run", "python", "scripts/generate_parity_report.py", "--output", output_path],
        cwd=clone_dir,
        check=True,
        capture_output=True,
        text=True,
    )
    with open(output_path) as f:
        return json.load(f)


def transform_data(raw: dict, version: str) -> dict:
    """Transform parity report JSON into our dashboard schema."""
    services = []
    raw_services = raw.get("services", {})
    raw_summary = raw.get("summary", {})

    for name, svc in sorted(raw_services.items()):
        status = svc.get("status", "unknown")
        if status == "moto_backed":
            provider = "moto"
        elif status == "native":
            provider = "native"
        else:
            provider = status

        all_ops = svc.get("all_ops", [])
        implemented_ops_set = set(svc.get("implemented_ops", []))
        total_ops = svc.get("total_aws_ops", len(all_ops))
        implemented_count = svc.get("implemented_count", len(implemented_ops_set))
        coverage_pct = svc.get("impl_pct", 0.0)

        operations = []
        for op in sorted(all_ops):
            operations.append({
                "name": op,
                "implemented": op in implemented_ops_set,
            })

        services.append({
            "name": name,
            "provider": provider,
            "category": get_category(name),
            "description": svc.get("description", ""),
            "total_ops": total_ops,
            "implemented_ops": implemented_count,
            "coverage_pct": round(coverage_pct, 1),
            "operations": operations,
        })

    total_services = raw_summary.get("total_services", len(services))
    native_services = raw_summary.get("native_services", sum(1 for s in services if s["provider"] == "native"))
    moto_services = raw_summary.get("moto_backed_services", sum(1 for s in services if s["provider"] == "moto"))
    total_ops = raw_summary.get("total_aws_operations", sum(s["total_ops"] for s in services))
    implemented_ops = raw_summary.get("total_implemented", sum(s["implemented_ops"] for s in services))
    coverage_pct = raw_summary.get("impl_pct", (implemented_ops / total_ops * 100) if total_ops > 0 else 0)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "robotocore_version": version,
        "summary": {
            "total_services": total_services,
            "native_services": native_services,
            "moto_services": moto_services,
            "total_ops": total_ops,
            "implemented_ops": implemented_ops,
            "coverage_pct": round(coverage_pct, 1),
        },
        "services": services,
    }


def write_output(data: dict) -> None:
    """Write coverage.json to data/ and site/data/ atomically."""
    output_paths = [
        PROJECT_ROOT / "data" / "coverage.json",
        PROJECT_ROOT / "site" / "data" / "coverage.json",
    ]
    json_str = json.dumps(data, indent=2)

    for path in output_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json_str)
        tmp.rename(path)
        print(f"Wrote {path}")


def main():
    tmpdir = tempfile.mkdtemp(prefix="robotocore-extract-")
    try:
        clone_dir = clone_repo(tmpdir)
        version = get_version(clone_dir)
        print(f"robotocore version: {version}")

        report_path = os.path.join(tmpdir, "parity_report.json")
        raw = run_parity_report(clone_dir, report_path)
        data = transform_data(raw, version)

        print(f"Extracted {len(data['services'])} services, "
              f"{data['summary']['implemented_ops']}/{data['summary']['total_ops']} ops "
              f"({data['summary']['coverage_pct']}% coverage)")

        write_output(data)
        print("Done.")
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e.cmd}", file=sys.stderr)
        if e.stdout:
            print(f"stdout: {e.stdout}", file=sys.stderr)
        if e.stderr:
            print(f"stderr: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
