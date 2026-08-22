class CB:
    HOME = "menu_home"
    CONNECT = "menu_connect"
    SUBSCRIPTION = "menu_subscription"
    DEVICES = "menu_devices"
    HELP = "menu_help"
    PROFILE = "menu_profile"

    START_TRIAL = "start_trial"
    START_HOW = "start_how"

    CONNECT_GET_LINK = "connect_get_link"
    CONNECT_INSTRUCTIONS = "connect_instructions"

    SUBSCRIPTION_BUY = "subscription_buy"
    SUBSCRIPTION_EXTEND = "subscription_extend"

    DEVICES_LIST = "devices_list"
    DEVICES_ADD = "devices_add"
    DEVICES_MANAGE = "devices_remove"
    DEVICES_REVOKE_PREFIX = "dev_rv:"

    HELP_CONNECTION = "help_connection"
    HELP_LINK = "help_link"
    HELP_SPEED = "help_speed"
    HELP_DEVICE = "help_device"
    HELP_SUPPORT = "help_support"

    @classmethod
    def revoke_device(cls, device_id: int) -> str:
        return f"{cls.DEVICES_REVOKE_PREFIX}{device_id}"

    @classmethod
    def parse_revoke_device(cls, data: str) -> int | None:
        if not data.startswith(cls.DEVICES_REVOKE_PREFIX):
            return None
        raw = data.removeprefix(cls.DEVICES_REVOKE_PREFIX)
        return int(raw) if raw.isdigit() else None
