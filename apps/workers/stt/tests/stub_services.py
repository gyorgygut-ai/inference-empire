import base64
import binascii

from dist.contract_stt_audio_transcriptions import Input, Output

TRANSCRIPT = "Sample transcription text"


def stt_transcriber_stub(request: Input) -> Output:
    """Deterministic STT stub mirroring the real worker's validation."""
    try:
        audio = base64.b64decode(request.file_base64, validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValueError("Audio file must be valid base64") from error
    if not audio:
        raise ValueError("Audio file is empty")
    if audio[:4] != b"RIFF":
        raise ValueError("Audio file must be valid WAV")
    return Output(text=TRANSCRIPT)
