from aiogram.fsm.state import State, StatesGroup


class DeviceStates(StatesGroup):
    waiting_name = State()
