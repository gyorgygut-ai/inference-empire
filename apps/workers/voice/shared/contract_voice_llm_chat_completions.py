from pydantic import BaseModel, ConfigDict, Field


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str = Field(pattern="^(system|user|assistant)$")
    content: str


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str = Field(min_length=1)
    messages: list[Message] = Field(min_length=1)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=128, gt=0, le=4096)


class ResponseMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str
    content: str


class Choice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: int
    message: ResponseMessage
    finish_reason: str


class Usage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)


class Output(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    object: str
    created: int = Field(ge=0)
    model: str = Field(min_length=1)
    choices: list[Choice] = Field(min_length=1)
    usage: Usage
