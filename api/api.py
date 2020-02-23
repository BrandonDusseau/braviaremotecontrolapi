from braviaproapi import BraviaClient
from braviaproapi.bravia import VolumeDevice, ButtonCode
from braviaproapi.bravia.errors import ApiError, AppLaunchError
from flask import Flask, request, abort
from functools import wraps
from fuzzywuzzy import fuzz
import re

app = Flask(__name__)
auth_key = None
bravia = None

def init(auth, host, psk):
    if auth is None or type(auth) is not str:
        print("The API key is not set. Set the BRAVIA_API_KEY environment variable and try again.")
        exit(4)

    if len(auth) < 32:
        print("The API key must be at least 32 characters to start the API.")
        exit(4)

    if host is None:
        print("The hostname of the target television is not set.\n"
              "Set the BRAVIA_DEVICE_HOST environment variable and try again.")
        exit(4)

    if psk is None:
        print("The pre-shared key of the target television is not set.\n"
              "Set the BRAVIA_DEVICE_PASSCODE environment variable and try again.")
        exit(4)

    global auth_key, bravia
    auth_key = auth
    bravia = BraviaClient(host, psk)


def require_appkey(view_function):
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        if request.headers.get("X-Auth-Key") == auth_key:
            return view_function(*args, **kwargs)
        else:
            abort(401)
    return decorated_function


@app.route("/power/<status>/", methods=["POST"])
@require_appkey
def power(status):
    try:
        if status.lower() == "on":
            bravia.system.power_on()
        elif status.lower() == "off":
            bravia.system.power_off()
        else:
            return __error("Invalid power status specified, must be 'on' or 'off'", 400)
    except ApiError as ex:
        return __error(str(ex), 500)
    return __success()


@app.route("/power/", methods=["GET"])
@require_appkey
def get_power():
    try:
        status = bravia.system.get_power_status()
    except ApiError as ex:
        return __error(str(ex), 500)

    response = __success()
    response["is_awake"] = status
    return response


@app.route("/volume/set/<level>/", methods=["POST"])
@require_appkey
def volume_set(level):
    try:
        level_num = int(level)
    except TypeError:
        return __error("level must be an integer value", 400)

    if level_num < 0 or level_num > 100:
        return __error("level must be between 0 and 100", 400)

    try:
        bravia.audio.set_volume_level(level_num)
    except ApiError as ex:
        return __error(str(ex), 500)

    return __success()


@app.route("/volume/mute/", methods=["POST"])
@require_appkey
def volume_mute():
    try:
        bravia.audio.mute()
    except ApiError as ex:
        return __error(str(ex), 500)

    return __success()


@app.route("/volume/unmute/", methods=["POST"])
@require_appkey
def volume_unmute():
    try:
        bravia.audio.unmute()
    except ApiError as ex:
        return __error(str(ex), 500)

    return __success()


@app.route("/volume/", methods=["GET"])
@require_appkey
def get_volume():
    try:
        vol_info = bravia.audio.get_volume_information()
    except ApiError as ex:
        return __error(str(ex), 500)

    speaker_vol = None
    for device in vol_info:
        if device.get("type") == VolumeDevice.SPEAKERS:
            speaker_vol = device
            break

    if speaker_vol is None:
        return __error("Speaker volume information is unavailable", 500)

    response = __success()
    response["volume"] = {
        "muted": speaker_vol.get("muted"),
        "level": speaker_vol.get("volume")
    }
    return response


@app.route("/apps/launch/<app_name>", methods=["POST"])
@require_appkey
def app_launch(app_name):
    try:
        app_list = bravia.appcontrol.get_application_list(exclude_builtin=True)
    except ApiError as ex:
        return __error(str(ex), 500)

    best_match_ratio = 0
    best_match = None
    for current_app in app_list:
        ratio = fuzz.ratio(app_name.lower(), current_app.get("name").lower())
        if ratio > 50 and ratio > best_match_ratio:
            best_match_ratio = ratio
            best_match = current_app

    if best_match is None:
        return __error("Could not locate app", 404)

    try:
        bravia.appcontrol.set_active_app(best_match.get("uri"))
    except (ApiError, AppLaunchError) as ex:
        return __error(str(ex), 500)

    response = __success()
    response["app_name"] = best_match.get("name")
    return response


@app.route("/apps/", methods=["GET"])
@require_appkey
def get_app():
    try:
        app_list = bravia.appcontrol.get_application_list(exclude_builtin=True)
    except ApiError as ex:
        return __error(str(ex), 500)

    if app_list is not None:
        app_names = [app_info.get("name") for app_info in app_list]
    else:
        app_names = []

    response = __success()
    response["apps"] = app_names
    return response


@app.route("/home/", methods=["POST"])
@require_appkey
def home():
    try:
        bravia.remote.send_button(ButtonCode.HOME)
    except ApiError as ex:
        return __error(str(ex), 500)

    return __success()


@app.route("/playback/<action>/", methods=["POST"])
@require_appkey
def playback(action):
    try:
        if action.lower() == "play":
            bravia.remote.send_button(ButtonCode.PLAY)
        elif action.lower() == "pause":
            bravia.remote.send_button(ButtonCode.PAUSE)
        elif action.lower() == "forward":
            bravia.remote.send_button(ButtonCode.FLASH_PLUS)
        elif action.lower() == "reverse":
            bravia.remote.send_button(ButtonCode.FLASH_MINUS)
        elif action.lower() == "next":
            bravia.remote.send_button(ButtonCode.NEXT)
        elif action.lower() == "previous":
            bravia.remote.send_button(ButtonCode.PREV)
        elif action.lower() == "stop":
            bravia.remote.send_button(ButtonCode.STOP)
        else:
            return __error(
                ("Invalid playback command. Must be 'play', 'pause', 'stop', 'next', 'previous', 'forward', or"
                 " 'reverse'."),
                400
            )
    except ApiError as ex:
        return __error(str(ex), 500)

    return __success()


@app.route("/input/set/<input>/", methods=["POST"])
@require_appkey
def input_set(input):
    try:
        input_list = bravia.avcontent.get_external_input_status()
    except ApiError as ex:
        return __error(str(ex), 500)

    best_match_ratio = 0
    best_match = None
    for current_input in input_list:
        if current_input.get("name") is None:
            continue

        name_ratio = fuzz.token_set_ratio(input.lower(), current_input.get("name").lower())
        if name_ratio > 50 and name_ratio > best_match_ratio:
            best_match_ratio = name_ratio
            best_match = current_input

        if current_input.get("custom_label") is not None:
            label_ratio = fuzz.token_set_ratio(input.lower(), current_input.get("custom_label").lower())
            if label_ratio > 50 and label_ratio > best_match_ratio:
                best_match_ratio = label_ratio
                best_match = current_input

    if best_match is None:
        return __error("Could not locate input", 404)

    try:
        bravia.avcontent.set_play_content(best_match.get("uri"))
    except ApiError as ex:
        return __error(str(ex), 500)

    response = __success()
    response["input"] = {
        "name": best_match.get("name"),
        "custom_label": best_match.get("custom_label")
    }
    return response


@app.route("/input/", methods=["GET"])
@require_appkey
def get_input():
    try:
        current_input = bravia.avcontent.get_playing_content_info()
    except ApiError as ex:
        return __error(str(ex), 500)

    if current_input is None:
        return __error("Not currently displaying an external input", 404)

    response = __success()
    response["input_name"] = current_input.get("name")
    return response


@app.route("/input/all/", methods=["GET"])
@require_appkey
def get_all_inputs():
    try:
        inputs = bravia.avcontent.get_external_input_status()
    except ApiError as ex:
        return __error(str(ex), 500)

    input_list = []
    if inputs is not None:
        for input in inputs:
            input_list.append({
                "name": input.get("name"),
                "custom_label": input.get("custom_label")
            })

    response = __success()
    response["inputs"] = input_list
    return response


@app.route("/channel/", methods=["GET"])
@require_appkey
def get_channels():
    try:
        channels = __get_tv_channels()
    except ApiError as ex:
        return __error(str(ex), 500)

    output_channels = []
    for channel in channels:
        channel_info = channel.get("channel_info")
        if channel_info is not None:
            channel_number = channel_info.get("channel_full")
            channel_visible = channel_info.get("visible", False)

        if not channel_visible:
            continue

        output_channels.append({
            "channel": channel_number,
            "type": channel.get("type"),
            "name": channel.get("name")
        })

    response = __success()
    response["channels"] = output_channels
    return response


@app.route("/channel/number/<input>/", methods=["POST"])
@require_appkey
def set_channel_by_number(input):
    channel_input = re.fullmatch(r"^(?P<main>\d+)([.-](?P<sub>\d+))?$", input)
    if channel_input is None:
        return __error("Channel number must be in numeric format 'X' or 'X.Y' or 'X-Y'", 400)
    selected_main = channel_input.group('main')
    try:
        selected_sub = channel_input.group('sub')
    except IndexError:
        selected_sub = None

    try:
        matching_channel = __locate_matching_channel_by_number(selected_main, selected_sub)
    except ApiError as ex:
        return __error(str(ex), 500)

    if matching_channel is None:
        return __error("The selected channel is not available", 404)

    channel_uri = matching_channel.get("uri")
    if channel_uri is None:
        return __error("A channel was found but was invalid", 500)

    try:
        bravia.avcontent.set_play_content(channel_uri)
    except ApiError as ex:
        return __error(str(ex), 500)

    response = __success()
    matching_channel_info = matching_channel.get("channel_info", {})
    response["channel"] = matching_channel_info.get("channel_full")
    response["name"] = matching_channel.get("name")
    response["type"] = matching_channel.get("type")
    return response


@app.route("/channel/name/<channel_name>", methods=["POST"])
@require_appkey
def set_channel_by_name(channel_name):
    try:
        # Analog channels do not have names, so we'll save some time here.
        channels = __get_tv_channels(exclude_analog=True)
    except ApiError as ex:
        return __error(str(ex), 500)

    best_match_ratio = 0
    matching_channel = None
    for channel in channels:
        channel_info = channel.get("channel_info", {})
        channel_visible = channel_info.get("visible", False)

        if not channel_visible:
            continue

        ratio = fuzz.ratio(channel_name.lower(), channel.get("name").lower())
        if ratio > 50 and ratio > best_match_ratio:
            best_match_ratio = ratio
            matching_channel = channel

    if matching_channel is None:
        return __error("Could not locate a matching channel", 404)

    channel_uri = matching_channel.get("uri")
    if channel_uri is None:
        return __error("A channel was found but was invalid", 500)

    try:
        bravia.avcontent.set_play_content(channel_uri)
    except ApiError as ex:
        return __error(str(ex), 500)

    response = __success()
    matching_channel_info = matching_channel.get("channel_info", {})
    response["channel"] = matching_channel_info.get("channel_full")
    response["name"] = matching_channel.get("name")
    response["type"] = matching_channel.get("type")
    return response


def __locate_matching_channel_by_number(selected_main, selected_sub):
    exclude_analog = selected_sub is not None

    channels = __get_tv_channels(exclude_analog)

    matching_analog = None
    matching_digital = None
    for channel in channels:
        channel_info = channel.get("channel_info", {})
        channel_main = channel_info.get("channel_main")
        channel_sub = channel_info.get("channel_sub")
        channel_visible = channel_info.get("visible", False)

        if not channel_visible:
            continue

        if channel["type"] == "analog" and channel_main == selected_main and selected_sub is None:
            matching_analog = channel
        elif channel["type"] == "digital" and channel_main == selected_main:
            if ((selected_sub is None and channel_sub == "1")
                    or (selected_sub is not None and channel_sub == selected_sub)):
                matching_digital = channel

    return matching_analog or matching_digital


def __get_tv_channels(exclude_analog=False):
    if not exclude_analog:
        analog_channels = bravia.avcontent.get_content_list("tv:analog")
        if analog_channels is None:
            analog_channels = []
        for channel in analog_channels:
            channel.update({"type": "analog"})
    else:
        analog_channels = []

    digital_channels = bravia.avcontent.get_content_list("tv:atsct")
    if digital_channels is None:
        digital_channels = []
    for channel in digital_channels:
        channel.update({"type": "digital"})

    return analog_channels + digital_channels


def __success():
    return {"status": "ok"}


def __error(message, status):
    return (
        {
            "status": "error",
            "error": message
        },
        status
    )
