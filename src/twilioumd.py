from twilio.rest import Client
import utils
import sys

# Initialize logging
import logging
from loguru import logger

logger.remove()
logger.add(sys.stdout, format="{time} {level} {message}")
logger = logging.getLogger()
logger.setLevel(logging.INFO)

account_sid = utils.get_ssm_param("twilioAccountSid")
auth_token = utils.get_ssm_param("twilioAuthToken")
client = Client(account_sid, auth_token)

# Base URL of API
http_api_base = utils.get_ssm_param("apiSandboxHttpBase")


def twilio_redirect_twiml(call_sid):
    """
    Redirects back to the main answer handler when audio is finished playing
    :param call_sid:
    :return:
    """
    client.calls(sid=call_sid).update(
        twiml=f'<Response><Redirect>https://{http_api_base}/twilio/answer/</Redirect></Response>')
