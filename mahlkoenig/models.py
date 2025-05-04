from datetime import datetime, timedelta
from enum import Enum
from typing import Union

from .exceptions import ProtocolError

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeInt,
    TypeAdapter,
    ValidationError,
    field_validator,
)
from pydantic.alias_generators import to_pascal
from pydantic.networks import IPvAnyAddress
from pydantic_extra_types.mac_address import MacAddress


class AutoSleepTimePreset(int, Enum):
    MIN_3 = 180
    MIN_5 = 300
    MIN_10 = 600
    MIN_20 = 1200
    MIN_30 = 1800

    def __str__(self) -> str:
        return f"{self.value // 60} min"


class BrewType(int, Enum):
    SINGLE_SHOT = 1
    DOUBLE_SHOT = 2
    V60 = 3
    CHEMEX = 4
    NAKED = 5
    SINGLE_CUP = 6
    DOUBLE_CUP = 7

    def __str__(self) -> str:
        return self.name.replace("_", " ").title()


class MessageType(str, Enum):
    Login = "Login"
    MachineInfo = "MachineInfo"
    SystemStatus = "SystemStatus"
    AutoSleepTime = "AutoSleepTime"
    RecipeList = "RecipeList"
    WifiInfo = "WifiInfo"


# ────────── payloads ──────────
#
class Statistics(BaseModel):
    system_restarts: int
    total_grind_shots: int
    total_grind_time: timedelta
    recipe_1_grind_shots: int
    recipe_1_grind_time: timedelta
    recipe_2_grind_shots: int
    recipe_2_grind_time: timedelta
    recipe_3_grind_shots: int
    recipe_3_grind_time: timedelta
    recipe_4_grind_shots: int
    recipe_4_grind_time: timedelta
    manual_mode_grind_shots: int
    manual_mode_grind_time: timedelta
    disc_life_time: timedelta
    total_on_time: timedelta
    standby_time: timedelta
    total_motor_on_time: timedelta
    total_errors_01: int
    total_errors_02: int
    total_errors_03: int
    total_errors_04: int
    total_errors_08: int
    total_errors_09: int
    total_errors_10: int

    model_config = ConfigDict(alias_generator=to_pascal)

    @field_validator(
        "total_grind_time",
        "recipe_1_grind_time",
        "recipe_2_grind_time",
        "recipe_3_grind_time",
        "recipe_4_grind_time",
        "manual_mode_grind_time",
        "disc_life_time",
        "total_on_time",
        "standby_time",
        "total_motor_on_time",
        mode="before",
    )
    def _str_to_int(cls, value: str) -> int:
        return int(value)


class NetworkModel(BaseModel):
    ap_mac_address: MacAddress | None
    current_ap_ipv4: IPvAnyAddress | None
    sta_mac_address: MacAddress
    current_sta_ipv4: IPvAnyAddress

    @field_validator("ap_mac_address", "current_ap_ipv4", mode="before")
    @classmethod
    def empty_to_none(cls, value: str) -> str | None:
        if value == "":
            return None
        return value


class MachineInfo(NetworkModel):
    serial_no: str
    product_no: str
    sw_version: str
    sw_build_no: NonNegativeInt
    disc_life_time: timedelta
    hostname: str

    model_config = ConfigDict(extra="forbid", alias_generator=to_pascal)


class SystemStatus(BaseModel):
    grind_running: bool
    error_code: str
    active_menu: NonNegativeInt
    grind_time: timedelta = Field(alias="GrindTimeMs")

    @field_validator("grind_time", mode="after")
    @classmethod
    def from_milliseconds(cls, value: timedelta) -> timedelta:
        return timedelta(milliseconds=value.total_seconds())

    model_config = ConfigDict(extra="forbid", alias_generator=to_pascal)


class WifiInfo(NetworkModel):
    wifi_mode: int

    model_config = ConfigDict(extra="forbid", alias_generator=to_pascal)


class Recipe(BaseModel):
    recipe_no: NonNegativeInt
    grind_time: timedelta
    name: str
    bean_name: str
    grinding_degree: NonNegativeInt
    brewing_type: BrewType
    guid: str
    last_modify_index: NonNegativeInt
    last_modify_time: datetime

    @field_validator("grind_time", mode="after")
    @classmethod
    def from_deciseconds(cls, value: timedelta) -> timedelta:
        return timedelta(milliseconds=100 * value.total_seconds())

    model_config = ConfigDict(extra="forbid", alias_generator=to_pascal)


class ResponseStatus(BaseModel):
    source_message: MessageType
    success: bool
    reason: str

    model_config = ConfigDict(extra="forbid", alias_generator=to_pascal)


# ────────── responses ──────────


class ResponseMessage(BaseModel):
    msg_id: int
    session_id: int

    model_config = ConfigDict(extra="forbid", alias_generator=to_pascal)


class MachineInfoMessage(ResponseMessage):
    machine_info: MachineInfo

    model_config = ConfigDict(extra="forbid", alias_generator=to_pascal)


class SystemStatusMessage(ResponseMessage):
    system_status: SystemStatus

    model_config = ConfigDict(extra="forbid", alias_generator=to_pascal)


class WifiInfoMessage(ResponseMessage):
    wifi_info: WifiInfo

    model_config = ConfigDict(extra="forbid", alias_generator=to_pascal)


class AutoSleepMessage(ResponseMessage):
    auto_sleep_time: AutoSleepTimePreset

    model_config = ConfigDict(extra="forbid", alias_generator=to_pascal)


class RecipeMessage(ResponseMessage):
    recipe: Recipe

    model_config = ConfigDict(extra="forbid", alias_generator=to_pascal)


class ResponseStatusMessage(ResponseMessage):
    response_status: ResponseStatus

    model_config = ConfigDict(extra="forbid", alias_generator=to_pascal)


ResponseMessages = Union[
    MachineInfoMessage,
    SystemStatusMessage,
    WifiInfoMessage,
    AutoSleepMessage,
    RecipeMessage,
    ResponseStatusMessage,
]

# ────────── requests ──────────


class RequestMessage(BaseModel):
    msg_id: int = 0  # Will be set by client
    session_id: int = 0  # Will be set by client

    model_config = ConfigDict(
        extra="forbid",
        alias_generator=to_pascal,
        validate_by_name=True,
        serialize_by_alias=True,
        populate_by_name=True,
    )


class LoginRequest(RequestMessage):
    login: str


class SimpleRequest(RequestMessage):
    request_type: MessageType


class SetAutoSleepTimeRequest(RequestMessage):
    auto_sleep_time: AutoSleepTimePreset


RequestMessages = Union[
    LoginRequest,
    SimpleRequest,
    SetAutoSleepTimeRequest,
]


_ADAPTER = TypeAdapter(ResponseMessages)


def parse(data: dict) -> ResponseMessage:
    try:
        return _ADAPTER.validate_python(data)
    except ValidationError as ex:
        raise ProtocolError(f"Cannot parse {data!r}\n Exception {ex}") from ex


def parse_statistics(text: str) -> Statistics:
    stats: dict[str, str] = {}

    for line in text.splitlines():
        match line.strip().rstrip(";").split(";", 1):
            case [key, value]:
                stats[key] = value
            case _:
                pass

    return Statistics(**stats)
