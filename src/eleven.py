import sys
import utils
from elevenlabs import generate, Voice, VoiceSettings
from elevenlabs_monkey_patch import apply_patch
from aws_xray_sdk.core import xray_recorder
# Initialize logging
import logging
from loguru import logger

logger.remove()
logger.add(sys.stdout, format="{time} {level} {message}")
logger = logging.getLogger()
logger.setLevel(logging.INFO)

apply_patch()


def say_stream(text):
    """
      Streams audio to the websocket from elevenlabs back to Twilio and send a mark
      message to Twilio to signal the end of the audio stream.  This must be invoked
      asynchronously.

      For Eleven Labs API returns we must use the Monkey Patch for the moment to get PCM audio instead of MP3.
      We need to down sample the audio from 16kHz to 8kHz and convert from PCM to µ-law for twilio.
      The conversion is done using pydub and pydub using ffmpeg, so we need to install ffmpeg in the Dockerfile.
      """
    # TODO: The chunk size should be a multiple of the sample size to avoid any cut-off or padding issues.
    logger.info(f"Calling eleven labs with text length: {len(text)} and text: {text}")
    elevenlabs_api_key = utils.get_ssm_param('elevenLabsApiKey')
    voice_id = utils.get_ssm_param('elevenLabsVoiceId')
    logger.info(f"Eleven labs API key first 4 chars (avoid max chars error): {elevenlabs_api_key[:4]}")
    xray_recorder.begin_subsegment('eleven_labs_generate_stream')
    xray_recorder.put_metadata('eleven_labs_text_to_generate', text)
    audio_stream = generate(
        text=text,
        api_key=elevenlabs_api_key,
        stream_chunk_size=2048,
        latency=4,
        model="eleven_monolingual_v1",
        voice=Voice(
            voice_id=voice_id,
            settings=VoiceSettings(stability=0.71, similarity_boost=0.5, style=0.0, use_speaker_boost=True)
        ),
        stream=True
    )
    xray_recorder.end_subsegment()
    return audio_stream
