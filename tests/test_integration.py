"""End-to-end AWS integration test.

Creates a real IAM user, launches an EC2 instance, SSHes in, and cleans up.
Requires live AWS credentials with admin-level IAM and EC2 permissions.

Run with:  pytest -m integration
"""
from __future__ import annotations

import io
import time
import uuid
from typing import Generator

import boto3
import paramiko
import pytest
from botocore.exceptions import ClientError, WaiterError

from edutools.iam import IAMProvisioner

# All resources are in us-west-2
REGION = "us-west-2"

# SSM parameter for the latest Amazon Linux 2023 AMI
AL2023_SSM_PARAM = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"

# Instance type (free-tier eligible)
INSTANCE_TYPE = "t2.micro"

# Unique prefix to tag and identify test resources
TEST_PREFIX = "edutools-integ"

# Timeouts (seconds)
IAM_PROPAGATION_MAX_WAIT = 120
INSTANCE_RUNNING_TIMEOUT = 180
SSH_READY_TIMEOUT = 120
INSTANCE_TERMINATED_TIMEOUT = 300


def _retry(
    fn: object,
    *,
    max_wait: float = 60,
    initial_delay: float = 5.0,
    backoff_factor: float = 1.5,
    retryable_codes: tuple[str, ...] = (
        "AuthFailure",
        "InvalidClientTokenId",
        "AccessDenied",
    ),
) -> object:
    """Retry a callable until it succeeds or *max_wait* is exhausted.

    Handles IAM eventual consistency: newly created access keys may not
    be recognized by EC2 for 10-30 seconds.
    """
    deadline = time.monotonic() + max_wait
    delay = initial_delay
    last_exc: ClientError | None = None

    while time.monotonic() < deadline:
        try:
            return fn()  # type: ignore[operator]
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code not in retryable_codes:
                raise
            last_exc = e
            sleep_time = min(delay, deadline - time.monotonic())
            if sleep_time <= 0:
                break
            time.sleep(sleep_time)
            delay *= backoff_factor

    assert last_exc is not None
    raise last_exc


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def ami_id() -> str:
    """Resolve the latest Amazon Linux 2023 AMI ID via SSM Parameter Store."""
    ssm = boto3.client("ssm", region_name=REGION)
    resp = ssm.get_parameter(Name=AL2023_SSM_PARAM)
    return resp["Parameter"]["Value"]


@pytest.fixture(scope="module")
def test_user() -> Generator[dict[str, str], None, None]:
    """Create a temporary IAM user with EC2 policy and access keys.

    Yields a dict with keys: username, access_key_id, secret_access_key.
    Teardown deletes the user and all associated resources.
    """
    provisioner = IAMProvisioner(region_name=REGION)
    admin_iam = boto3.client("iam", region_name=REGION)
    username = f"{TEST_PREFIX}-{uuid.uuid4().hex[:8]}"

    # --- Setup ---
    provisioner.create_user(username)
    provisioner.attach_ec2_policy(username)

    keys_resp = admin_iam.create_access_key(UserName=username)
    access_key_id: str = keys_resp["AccessKey"]["AccessKeyId"]
    secret_access_key: str = keys_resp["AccessKey"]["SecretAccessKey"]

    yield {
        "username": username,
        "access_key_id": access_key_id,
        "secret_access_key": secret_access_key,
    }

    # --- Teardown ---
    provisioner.delete_user(username)


@pytest.fixture(scope="module")
def test_ec2_client(test_user: dict[str, str]) -> boto3.client:
    """EC2 client authenticated as the test user."""
    session = boto3.Session(
        aws_access_key_id=test_user["access_key_id"],
        aws_secret_access_key=test_user["secret_access_key"],
        region_name=REGION,
    )
    return session.client("ec2")


# ---------------------------------------------------------------------------
# Integration test
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestEC2EndToEnd:
    """Full lifecycle: IAM user -> key pair -> security group -> EC2 -> SSH -> cleanup."""

    def test_full_ec2_lifecycle(
        self,
        test_user: dict[str, str],
        test_ec2_client: object,
        ami_id: str,
    ) -> None:
        ec2 = test_ec2_client
        unique_id = uuid.uuid4().hex[:8]
        key_name = f"{TEST_PREFIX}-key-{unique_id}"
        sg_name = f"{TEST_PREFIX}-sg-{unique_id}"
        instance_id: str | None = None
        sg_id: str | None = None

        try:
            # Step 1: Create key pair (retry for IAM credential propagation)
            key_resp = _retry(
                lambda: ec2.create_key_pair(KeyName=key_name),  # type: ignore[union-attr]
                max_wait=IAM_PROPAGATION_MAX_WAIT,
            )
            private_key_pem: str = key_resp["KeyMaterial"]  # type: ignore[index]

            # Step 2: Create security group in default VPC
            vpcs = ec2.describe_vpcs(  # type: ignore[union-attr]
                Filters=[{"Name": "isDefault", "Values": ["true"]}]
            )
            vpc_id: str = vpcs["Vpcs"][0]["VpcId"]

            sg_resp = ec2.create_security_group(  # type: ignore[union-attr]
                GroupName=sg_name,
                Description="edutools integration test - SSH access",
                VpcId=vpc_id,
            )
            sg_id = sg_resp["GroupId"]

            ec2.authorize_security_group_ingress(  # type: ignore[union-attr]
                GroupId=sg_id,
                IpPermissions=[
                    {
                        "IpProtocol": "tcp",
                        "FromPort": 22,
                        "ToPort": 22,
                        "IpRanges": [
                            {
                                "CidrIp": "0.0.0.0/0",
                                "Description": "SSH for integration test",
                            }
                        ],
                    }
                ],
            )

            # Step 3: Launch EC2 instance
            run_resp = ec2.run_instances(  # type: ignore[union-attr]
                ImageId=ami_id,
                InstanceType=INSTANCE_TYPE,
                KeyName=key_name,
                SecurityGroupIds=[sg_id],
                MinCount=1,
                MaxCount=1,
                TagSpecifications=[
                    {
                        "ResourceType": "instance",
                        "Tags": [
                            {
                                "Key": "Name",
                                "Value": f"{TEST_PREFIX}-instance-{unique_id}",
                            },
                            {"Key": "edutools-test", "Value": "true"},
                        ],
                    }
                ],
            )
            instance_id = run_resp["Instances"][0]["InstanceId"]

            # Step 4: Wait for instance to be running
            waiter = ec2.get_waiter("instance_running")  # type: ignore[union-attr]
            waiter.wait(
                InstanceIds=[instance_id],
                WaiterConfig={
                    "Delay": 10,
                    "MaxAttempts": INSTANCE_RUNNING_TIMEOUT // 10,
                },
            )

            desc = ec2.describe_instances(InstanceIds=[instance_id])  # type: ignore[union-attr]
            public_ip: str | None = desc["Reservations"][0]["Instances"][0].get(
                "PublicIpAddress"
            )
            assert public_ip is not None, "Instance did not receive a public IP"

            # Step 5: SSH into the instance
            private_key = paramiko.RSAKey.from_private_key(
                io.StringIO(private_key_pem)
            )
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            connected = False
            ssh_deadline = time.monotonic() + SSH_READY_TIMEOUT

            while time.monotonic() < ssh_deadline:
                try:
                    ssh.connect(
                        hostname=public_ip,
                        username="ec2-user",  # Amazon Linux 2023 default
                        pkey=private_key,
                        timeout=10,
                        auth_timeout=10,
                        banner_timeout=10,
                    )
                    connected = True
                    break
                except (
                    paramiko.ssh_exception.NoValidConnectionsError,
                    paramiko.ssh_exception.SSHException,
                    OSError,
                    TimeoutError,
                ):
                    remaining = ssh_deadline - time.monotonic()
                    if remaining <= 0:
                        break
                    time.sleep(min(10.0, remaining))

            assert connected, f"Could not SSH to {public_ip} within {SSH_READY_TIMEOUT}s"

            # Step 6: Run a command to verify
            _stdin, stdout, _stderr = ssh.exec_command("echo hello-from-edutools")
            output = stdout.read().decode().strip()
            ssh.close()

            assert output == "hello-from-edutools", f"Unexpected SSH output: {output!r}"

        finally:
            # Cleanup — always runs, even on assertion failure
            errors: list[str] = []

            # 1. Terminate instance
            if instance_id is not None:
                try:
                    ec2.terminate_instances(InstanceIds=[instance_id])  # type: ignore[union-attr]
                    term_waiter = ec2.get_waiter("instance_terminated")  # type: ignore[union-attr]
                    term_waiter.wait(
                        InstanceIds=[instance_id],
                        WaiterConfig={
                            "Delay": 15,
                            "MaxAttempts": INSTANCE_TERMINATED_TIMEOUT // 15,
                        },
                    )
                except (ClientError, WaiterError) as e:
                    errors.append(f"terminate instance {instance_id}: {e}")

            # 2. Delete security group (retry for DependencyViolation)
            if sg_id is not None:
                sg_deadline = time.monotonic() + 60
                while time.monotonic() < sg_deadline:
                    try:
                        ec2.delete_security_group(GroupId=sg_id)  # type: ignore[union-attr]
                        break
                    except ClientError as e:
                        code = e.response.get("Error", {}).get("Code", "")
                        if code == "DependencyViolation":
                            time.sleep(10)
                            continue
                        errors.append(f"delete security group {sg_id}: {e}")
                        break

            # 3. Delete key pair
            try:
                ec2.delete_key_pair(KeyName=key_name)  # type: ignore[union-attr]
            except ClientError as e:
                errors.append(f"delete key pair {key_name}: {e}")

            if errors:
                print(f"CLEANUP ERRORS: {errors}")
