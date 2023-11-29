import sys
import json
import websocket_handler
import http_handler
import traceback

# Simple admin web interface
from app import handler as fastapi_handler

# X-Ray for performance monitoring
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

xray_recorder.configure(service='TwilioElevenLabsDemo')
patch_all()

# try to use it with automatic instrumenting first

# Initialize logging
import logging
from loguru import logger

logger.remove()
logger.add(sys.stdout, format="{time} {level} {message}")
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    logger.info("Start of Lambda function. Incoming event: " + str(event))

    # Future admin web interface
    # if event.get('path', '').startswith('/web'):
    #     return fastapi_handler(event, context)

    # we only handle the mark event from twilio marking the end of the audio and that start event from twilio
    is_websocket_event = (
            ('requestContext' in event and 'eventType' in event['requestContext']) or
            (event.get('event') == 'mark')
    )

    logger.info("is_websocket_event: " + str(is_websocket_event))
    # Used to stream audio from eleven labs to twilio
    if is_websocket_event:
        try:
            logger.info("Call handler for websocket event")
            return websocket_handler.handle(event)
        except Exception as e:
            logger.error(f"An error occurred: {e}")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': str(e)})
            }
    else:
        # Normal HTTP requests to navigate in twilio using twiml
        try:
            return http_handler.handler(event, context)
        except Exception as e:
            logger.error(f"An error occurred: {e}")
            traceback.print_exc()
            return {
                'statusCode': 500,
                'body': json.dumps({'error': str(e)})
            }
