from pydub import AudioSegment
import audioop
from aws_xray_sdk.core import xray_recorder


def convert_eleven_pcm_chunk_to_twilio_mulaw(chunk):
    # Convert from PCM with 16kHz sample rate to PCM with 8kHz sample rate
    # The audio is assumed to have 1 channel and 2 bytes per sample (16 bits per sample)
    xray_recorder.begin_subsegment('convert_pcm_to_mulaw')
    xray_recorder.put_metadata('pcm_chunk_length', len(chunk))
    pcm_audio = AudioSegment(
        data=chunk,
        sample_width=2,  # 16 bits per sample
        frame_rate=16000,  # 16kHz sample rate
        channels=1  # Mono
    )
    resampled_pcm_audio = pcm_audio.set_frame_rate(8000)  # Resampling to 8kHz
    resampled_pcm_bytes = resampled_pcm_audio.raw_data

    # Convert PCM to µ-law
    mulaw_bytes = audioop.lin2ulaw(resampled_pcm_bytes, 2)  # 2 bytes per sample (16 bits)
    xray_recorder.end_subsegment()
    return mulaw_bytes
