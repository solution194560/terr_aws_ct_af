# Copyright Amazon.com, Inc. or its affiliates. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import inspect
from typing import TYPE_CHECKING, Any, Dict

from aft_common import notifications
from aft_common.account_provisioning_framework import ProvisionRoles, tag_account
from aft_common.auth import AuthClient
from aft_common.logger import customization_request_logger
from boto3.session import Session

if TYPE_CHECKING:
    from aws_lambda_powertools.utilities.typing import LambdaContext
else:
    LambdaContext = object


def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> None:
    action = event["action"]
    event_payload = event["payload"]
    request_id = event_payload["customization_request_id"]
    account_info = event_payload["account_info"]["account"]
    target_account_id = event_payload["account_info"]["account"]["id"]

    logger = customization_request_logger(
        aws_account_id=target_account_id, customization_request_id=request_id
    )

    aft_management_session = Session()
    auth = AuthClient()

    try:
        rollback = False
        try:
            if event["rollback"]:
                rollback = True
        except KeyError:
            pass

        ct_management_session = auth.get_ct_management_session(
            role_name=ProvisionRoles.SERVICE_ROLE_NAME
        )

        if action == "tag_account":
            logger.info("Tag account Organization resource")
            tag_account(event_payload, account_info, ct_management_session, rollback)
        else:
            raise Exception(
                f"Incorrect Command Passed to Lambda Function. Input action: {action}. Expected: 'tag_account'"
            )

    except Exception as error:
        notifications.send_lambda_failure_sns_message(
            session=aft_management_session,
            message=str(error),
            context=context,
            subject="AFT account provisioning failed",
        )
        message = {
            "FILE": __file__.split("/")[-1],
            "METHOD": inspect.stack()[0][3],
            "EXCEPTION": str(error),
        }
        logger.exception(message)
        raise
