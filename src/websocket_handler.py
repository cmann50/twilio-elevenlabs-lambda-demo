import sys
import boto3
import base64
import eleven
import twilioumd
import utils
import json
import audioconvert
import re
# Initialize logging
import logging
from loguru import logger
from aws_xray_sdk.core import xray_recorder

logger.remove()
logger.add(sys.stdout, format="{time} {level} {message}")
logger = logging.getLogger()
logger.setLevel(logging.INFO)

client = boto3.client('apigatewaymanagementapi',
                      endpoint_url=f"https://{utils.get_ssm_param('apiSandboxWebsocketBase')}/sandbox")


def handle(event):
    #logger.info(f"Websocket accepted event: {event}")

    twilio_event_type = None

    if 'event' in event:
        twilio_event_type = event['event']
    else:
        body = json.loads(event['body'])
        twilio_event_type = body['event']

    try:
        if twilio_event_type == "start":
            logger.info("Start event received")
            body = json.loads(event['body'])
            call_sid = body['start']['callSid']
            aws_websocket_connection_id = event["requestContext"]["connectionId"]
            stream_sid = body['streamSid']
            textToSay = body['start']['customParameters']['textToSay']
            xray_recorder.begin_subsegment('stream_audio')
            xray_recorder.put_metadata('stream_audio_text', textToSay)
            stream_audio(stream_sid, aws_websocket_connection_id, textToSay, call_sid)
            xray_recorder.end_subsegment()
        elif twilio_event_type == "mark":
            logger.info("Mark event received")
            eoa_call_sid = event["mark"]["name"]
            call_sid = re.match(r'eoaCallSid(.+)', eoa_call_sid)[1]
            logger.info("Marked end of audio and redirecting back to main answer handler")
            xray_recorder.begin_subsegment('redirect_at_end_of_audio')
            twilioumd.twilio_redirect_twiml(call_sid)
            xray_recorder.end_subsegment()
    except Exception as e:
        logger.error(f"An exception occurred: {str(e)}")


def stream_audio(stream_sid, aws_websocket_connection_id, textToSay, call_sid):
    audio_stream = eleven.say_stream(textToSay)

    logger.info("Started eleven labs audio stream")
    for chunk in audio_stream:
        if chunk is not None:
            try:

                mulaw_bytes = audioconvert.convert_eleven_pcm_chunk_to_twilio_mulaw(chunk)

                message = {
                    "event": "media",
                    "streamSid": stream_sid,
                    "media": {
                        "payload": base64.b64encode(mulaw_bytes).decode('utf-8')
                    }
                }
                message_str = json.dumps(message)

                client.post_to_connection(
                    ConnectionId=aws_websocket_connection_id,
                    Data=message_str
                )

            except Exception as e:
                logger.error(f"Error in audio processing: {e}")

    logger.info(f"Done streaming audio. Sending mark event to mark end of stream")
    mark = {
        "event": "mark",
        "streamSid": stream_sid,
        "mark": {
            "name": f"eoaCallSid{call_sid}"
        }
    }
    message_str = json.dumps(mark)
    logger.info(f"Mark message dump: {message_str}")

    client.post_to_connection(
        ConnectionId=aws_websocket_connection_id,
        Data=message_str
    )
