from datetime import datetime, timezone
from ipaddress import IPv4Address

import pytest

from mahlkoenig.exceptions import ProtocolError
from mahlkoenig.models import (
    AutoSleepTimePreset,
    BrewType,
    MachineInfo,
    MachineInfoMessage,
    MessageType,
    parse,
)


def test_parse_machine_info_message():
    data = {
        "MsgId": 2,
        "SessionId": 1192944752,
        "MachineInfo": {
            "SerialNo": "1777D6",
            "ProductNo": "HEM-E54-HMI-P02.115",
            "SwVersion": "03.06",
            "SwBuildNo": 3,
            "DiscLifeTime": 130027,
            "Hostname": "x54grinder-1777d6",
            "ApMacAddress": "",
            "CurrentApIpv4": "192.168.4.1",
            "StaMacAddress": "c4:dd:57:c5:69:d4",
            "CurrentStaIpv4": "10.10.0.149",
        },
    }

    message = parse(data)
    assert isinstance(message, MachineInfoMessage)
    assert isinstance(message.machine_info, MachineInfo)
    assert message.msg_id == 2
    assert message.session_id == 1192944752
    assert message.machine_info.serial_no == "1777D6"
    assert message.machine_info.product_no == "HEM-E54-HMI-P02.115"
    assert message.machine_info.sw_version == "03.06"
    assert message.machine_info.sw_build_no == 3
    assert message.machine_info.disc_life_time.total_seconds() == 130027
    assert message.machine_info.hostname == "x54grinder-1777d6"
    assert message.machine_info.ap_mac_address is None
    assert message.machine_info.current_ap_ipv4 == IPv4Address("192.168.4.1")
    assert message.machine_info.sta_mac_address == "c4:dd:57:c5:69:d4"
    assert message.machine_info.current_sta_ipv4 == IPv4Address("10.10.0.149")


def test_parse_system_status_message():
    data = {
        "MsgId": 5,
        "SessionId": 1192944752,
        "SystemStatus": {
            "GrindRunning": False,
            "ErrorCode": "",
            "ActiveMenu": 4,
            "GrindTimeMs": 11800,
        },
    }

    message = parse(data)
    assert message.msg_id == 5
    assert message.session_id == 1192944752
    assert message.system_status.grind_running is False
    assert message.system_status.error_code == ""
    assert message.system_status.active_menu == 4
    assert message.system_status.grind_time.total_seconds() == 11.8


def test_parse_wifi_info_message():
    data = {
        "MsgId": 6,
        "SessionId": 1192944752,
        "WifiInfo": {
            "ApMacAddress": "",
            "CurrentApIpv4": "192.168.4.1",
            "StaMacAddress": "c4:dd:57:c5:69:d4",
            "CurrentStaIpv4": "10.10.0.149",
            "WifiMode": 1,
        },
    }

    message = parse(data)
    assert message.msg_id == 6
    assert message.session_id == 1192944752
    assert message.wifi_info.ap_mac_address is None
    assert message.wifi_info.current_ap_ipv4 == IPv4Address("192.168.4.1")
    assert message.wifi_info.sta_mac_address == "c4:dd:57:c5:69:d4"
    assert message.wifi_info.current_sta_ipv4 == IPv4Address("10.10.0.149")
    assert message.wifi_info.wifi_mode == 1


def test_parse_auto_sleep_message():
    data = {"MsgId": 7, "SessionId": 1192944752, "AutoSleepTime": 1800}

    message = parse(data)
    assert message.msg_id == 7
    assert message.session_id == 1192944752
    assert message.auto_sleep_time == AutoSleepTimePreset.MIN_30


def test_parse_recipe_message():
    data = {
        "MsgId": 193396736,
        "SessionId": 1192944752,
        "Recipe": {
            "RecipeNo": 1,
            "GrindTime": 115,
            "Name": "onetake",
            "BeanName": "Automatic",
            "GrindingDegree": 50,
            "BrewingType": 2,
            "Guid": "e408f736-0086-4e74-a28c-048ce0465202",
            "LastModifyIndex": 8,
            "LastModifyTime": 1728658412,
        },
    }

    message = parse(data)
    assert message.msg_id == 193396736
    assert message.session_id == 1192944752
    assert message.recipe.recipe_no == 1
    assert message.recipe.grind_time.total_seconds() == 11.5
    assert message.recipe.name == "onetake"
    assert message.recipe.bean_name == "Automatic"
    assert message.recipe.grinding_degree == 50
    assert message.recipe.brewing_type == BrewType.DOUBLE_SHOT
    assert message.recipe.guid == "e408f736-0086-4e74-a28c-048ce0465202"
    assert message.recipe.last_modify_index == 8

    expected_time = datetime.utcfromtimestamp(1728658412).replace(tzinfo=timezone.utc)
    assert message.recipe.last_modify_time == expected_time


def test_parse_response_status_message_success():
    data = {
        "MsgId": 8,
        "SessionId": 1192944752,
        "ResponseStatus": {
            "SourceMessage": "RecipeList",
            "Success": True,
            "Reason": "",
        },
    }

    message = parse(data)
    assert message.msg_id == 8
    assert message.session_id == 1192944752
    assert message.response_status.source_message == MessageType.RecipeList
    assert message.response_status.success is True
    assert message.response_status.reason == ""


def test_parse_response_status_message_error():
    data = {
        "MsgId": 8,
        "SessionId": 1192944752,
        "ResponseStatus": {
            "SourceMessage": "Login",
            "Success": False,
            "Reason": "Wrong credentials",
        },
    }

    message = parse(data)
    assert message.msg_id == 8
    assert message.session_id == 1192944752
    assert message.response_status.source_message == MessageType.Login
    assert message.response_status.success is False
    assert message.response_status.reason == "Wrong credentials"


def test_parse_raises_protocol_error_on_invalid_data():
    data = {"foo": "bar"}

    with pytest.raises(ProtocolError):
        parse(data)
