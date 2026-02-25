from aiogram.fsm.state import State, StatesGroup

class AdminStates(StatesGroup):
    waiting_for_code = State()
    waiting_for_video = State()
    waiting_for_channel_post = State()
    waiting_for_title = State()
    waiting_for_quality = State()
    waiting_for_expiration = State()
    waiting_for_code_delete = State()
    waiting_for_broadcast = State()

class UserStates(StatesGroup):
    entering_code = State()
    searching_name = State()
