# TODO: The ONLY thing this monkey patch is doing is adding this query parameter: &output_format=pcm_16000
# TODO: Remove this patch when they add the output_format param to the python API
# TODO: See https://github.com/elevenlabs/elevenlabs-python/issues/111
from typing import Iterator, Optional  # Monkey patch
from elevenlabs import TTS  # Monkey patch
from elevenlabs.api.model import Model  # Monkey patch
from elevenlabs.api.base import API, api_base_url_v1  # Monkey patch
from elevenlabs import Voice


def apply_patch():
    def my_generate_stream(
            text: str,
            voice: Voice,
            model: Model,
            stream_chunk_size: int = 2048,
            api_key: Optional[str] = None,
            latency: int = 1,
    ) -> Iterator[bytes]:
        url = f"{api_base_url_v1}/text-to-speech/{voice.voice_id}/stream?optimize_streaming_latency={latency}&output_format=pcm_16000"
        print("Monkey patch URL: " + url)
        data = dict(
            text=text,
            model_id=model.model_id,
            voice_settings=voice.settings.model_dump() if voice.settings else None,
        )  # type: ignore
        response = API.post(url, json=data, stream=True, api_key=api_key)
        for chunk in response.iter_content(chunk_size=stream_chunk_size):
            if chunk:
                yield chunk

    TTS.generate_stream = my_generate_stream  # Monkey patch
