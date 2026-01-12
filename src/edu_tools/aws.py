from __future__ import annotations

import os
from typing import Dict, List, Optional

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv


load_dotenv()


def _connect_client(region_name: Optional[str] = None):
    """Return an Amazon Connect client using the provided or default region."""
    region = region_name or os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
    session = boto3.session.Session(region_name=region) if region else boto3.session.Session()
    return session.client("connect")


def add_user_with_security_profile(
    username: str,
    first_name: str,
    last_name: str,
    email: str,
    password: Optional[str] = None,
    directory_user_id: Optional[str] = None,
    security_profile_ids: Optional[List[str]] = None,
    routing_profile_id: Optional[str] = None,
    instance_id: Optional[str] = None,
    phone_type: str = "SOFT_PHONE",
    auto_accept: bool = True,
    tags: Optional[Dict[str, str]] = None,
    region_name: Optional[str] = None,
) -> str:
    """Create an Amazon Connect user and attach one or more security profiles.

    Args:
        username: Login name for the user.
        first_name: Given name.
        last_name: Surname.
        email: Contact email address.
        password: Password for Amazon Connect-managed users. Required unless `directory_user_id` is provided.
        directory_user_id: Directory user identifier for SAML/AD-backed users. Required unless `password` is provided.
        security_profile_ids: List of security profile IDs. If omitted, `AWS_CONNECT_SECURITY_PROFILE_IDS` is used (comma separated).
        routing_profile_id: Routing profile ID. If omitted, `AWS_CONNECT_ROUTING_PROFILE_ID` is used.
        instance_id: Amazon Connect instance ID. If omitted, `AWS_CONNECT_INSTANCE_ID` is used.
        phone_type: Phone type for the user (for example, "SOFT_PHONE" or "DESK_PHONE").
        auto_accept: When using soft phone, whether to auto-accept contacts.
        tags: Optional tags to apply to the user.
        region_name: AWS region to target; falls back to AWS_REGION / AWS_DEFAULT_REGION.

    Returns:
        The created user's ID from Amazon Connect.
    """

    resolved_instance_id = instance_id or os.getenv("AWS_CONNECT_INSTANCE_ID")
    if not resolved_instance_id:
        raise ValueError("Instance ID is required; set AWS_CONNECT_INSTANCE_ID or pass instance_id.")

    resolved_routing_profile_id = routing_profile_id or os.getenv("AWS_CONNECT_ROUTING_PROFILE_ID")
    if not resolved_routing_profile_id:
        raise ValueError("Routing profile ID is required; set AWS_CONNECT_ROUTING_PROFILE_ID or pass routing_profile_id.")

    profiles = security_profile_ids
    if profiles is None:
        env_profiles = os.getenv("AWS_CONNECT_SECURITY_PROFILE_IDS", "")
        profiles = [p.strip() for p in env_profiles.split(",") if p.strip()]
    if not profiles:
        raise ValueError("At least one security profile ID is required; set AWS_CONNECT_SECURITY_PROFILE_IDS or pass security_profile_ids.")

    if not password and not directory_user_id:
        raise ValueError("Provide either password for Connect-managed users or directory_user_id for SAML/AD users.")

    identity_info: Dict[str, str] = {"FirstName": first_name, "LastName": last_name, "Email": email}
    phone_config: Dict[str, object] = {"PhoneType": phone_type}
    if phone_type == "SOFT_PHONE":
        phone_config["AutoAccept"] = auto_accept

    payload: Dict[str, object] = {
        "InstanceId": resolved_instance_id,
        "Username": username,
        "SecurityProfileIds": profiles,
        "RoutingProfileId": resolved_routing_profile_id,
        "IdentityInfo": identity_info,
        "PhoneConfig": phone_config,
    }
    if password:
        payload["Password"] = password
    if directory_user_id:
        payload["DirectoryUserId"] = directory_user_id
    if tags:
        payload["Tags"] = tags

    client = _connect_client(region_name)
    try:
        response = client.create_user(**payload)
    except ClientError as exc:
        message = exc.response.get("Error", {}).get("Message", str(exc))
        raise RuntimeError(f"Failed to create user {username}: {message}") from exc

    user_id = response.get("UserId")
    if not user_id:
        raise RuntimeError("Amazon Connect did not return a user ID.")
    return user_id
