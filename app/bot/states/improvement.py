from aiogram.fsm.state import State, StatesGroup


class ImprovementStates(StatesGroup):
    WAITING_FOR_IMPROVEMENT_INSTRUCTION = State()


class FreeformStates(StatesGroup):
    WAITING_FOR_PROMPT = State()


class ImageStates(StatesGroup):
    WAITING_FOR_PROMPT = State()
