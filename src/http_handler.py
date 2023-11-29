import utils
import sys
from twilio.twiml.voice_response import VoiceResponse
import json
from urllib.parse import urlparse
from urllib.parse import parse_qs
import base64
from aws_xray_sdk.core import xray_recorder
import query_lambda

# Initialize logging
import logging

from loguru import logger

logger.remove()
logger.add(sys.stdout, format="{time} {level} {message}")
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    logger.info(f"Route: {event['rawPath']}")
    route = event['rawPath']
    if route.endswith('/'):
        route = route[:-1]

    logger.info(f"Normalized route: {route}")


    if route == '/setvoice':
        response = set_voice(event)
    elif route == '/twilio/answer':
        decoded_body = decode_and_parse_body(event)
        logger.info(f"Decoded body: {decoded_body}")
        response = twilio_answer({**event, 'body': decoded_body}, decoded_body)
    elif route == '/twilio/respond':
        decoded_body = decode_and_parse_body(event)
        logger.info(f"Decoded body: {decoded_body}")
        response = twilio_respond({**event, 'body': decoded_body}, decoded_body)
    elif route == '/twilio/webhook/error':
        logger.info(f"Error to main error handler at /twilio/webhook/error: {json.dumps(event)}")
        return {
            'statusCode': 200
        }
    else:
        raise Exception('Invalid route')

    return response


def set_voice(event):
    logger.info(f"Set voice called with event: {event}")
    raw_query = event.get('rawQueryString', '')
    query_params = parse_qs(raw_query)
    voice_id = query_params.get('voiceId', [None])[0]
    if voice_id is None:
        return {
            'statusCode': 400,
            'body': json.dumps({'message': 'voiceId must be provided'})
        }
    utils.set_ssm_param("elevenLabsVoiceId", voice_id)
    return {
        'statusCode': 200,
        'body': json.dumps({'message': f'Voice set to {voice_id}'})
    }


def twilio_answer(event, decoded_body):
    logger.info(f"Twilio answer called with event: {event}")
    xray_recorder.begin_subsegment('twilio_answer')
    response = VoiceResponse()

    call_status = decoded_body['CallStatus']
    # When it first rings stream the intro message
    if call_status == 'ringing':
        websocket_url = f'wss://{utils.get_ssm_param("apiSandboxWebsocketBase")}/sandbox'
        response.connect().stream(url=websocket_url, name="my_stream", track='inbound_track').parameter(
            name='textToSay',
            value="I'm UMD Bot, how can I help you?")
        return utils.send_twiml(response)
        # response.say("I'm UMD Bot, how can I help you?")

    # Ask Twilio to listen for speech, convert it to text, and send it to the /twilio/respond/ endpoint
    response.gather(input='speech', action='/twilio/respond/', speechTimeout='auto',
                    speechModel='experimental_conversations')

    logger.info("Answer response: " + str(response))
    xray_recorder.end_subsegment()
    return utils.send_twiml(response)


def twilio_respond(event, decoded_body):
    logger.info(f"Twilio respond called with event: {event}")
    xray_recorder.begin_subsegment('twilio_respond')
    response = VoiceResponse()

    # If the user didn't say anything just return to gather
    if not decoded_body.get('SpeechResult'):
        logger.info("No speech result found. Returning to answer handler")
        response.redirect('/twilio/answer')
        return utils.send_twiml(response)

    speech_result = decoded_body['SpeechResult']
    logger.info(f"Twilio transcribed voice to text as: {speech_result}")

    chat_gpt_answer = query_lambda.query_chatgpt(speech_result)
    logger.info(f"Chat GPT answer (need to parse into string): {chat_gpt_answer}")

    websocket_url = f'wss://{utils.get_ssm_param("apiSandboxWebsocketBase")}/sandbox'
    response.connect().stream(url=websocket_url, name="my_stream", track='inbound_track').parameter(
        name='textToSay',
        value=chat_gpt_answer)

    logger.info("Respond response: " + str(response))
    xray_recorder.end_subsegment()
    return utils.send_twiml(response)


def decode_and_parse_body(event):
    logger.info("Entering decode_and_parse_body function with event: " + str(event))
    xray_recorder.begin_subsegment('decode_and_parse_body')

    decoded_body = event['body']

    # Decode base64 if necessary
    is_base64_encoded = event.get('isBase64Encoded', False)
    logger.info(f"isBase64Encoded: {is_base64_encoded}")

    if is_base64_encoded:
        decoded_body = base64.b64decode(event['body']).decode('utf-8')

    # Parse the main MIME type from the content-type header, ignoring additional parameters
    full_content_type = event['headers'].get('content-type', '')
    logger.info(f"Full content-type from headers: {full_content_type}")

    content_type = full_content_type.split(';')[0].strip()
    logger.info(f"Extracted content-type: {content_type}")

    # Parse based on content-type
    parsed_body = None
    if content_type == 'application/x-www-form-urlencoded':
        parsed_body = parse_qs(decoded_body)
        logger.info(f"Content parsed as form-urlencoded: {parsed_body}")

    elif content_type == 'application/json':
        parsed_body = json.loads(decoded_body)
        logger.info(f"Content parsed as JSON: {parsed_body}")

    if parsed_body is None:
        logger.info("Content type did not match known types. Returning as-is.")

    if parsed_body is not None:
        # Remove the list wrapper for single values
        for key, value in parsed_body.items():
            if isinstance(value, list) and len(value) == 1:
                parsed_body[key] = value[0]
        logger.info(f"Single values de-listed: {parsed_body}")
    else:
        logger.info("Content type did not match known types. Returning as-is.")

    xray_recorder.end_subsegment()
    return parsed_body or decoded_body
