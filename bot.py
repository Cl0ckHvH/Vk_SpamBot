import asyncio
import logging
import os
import random
from collections import deque

import toml
from vk import VK
from vk import types
from vk.bot_framework import Dispatcher, get_group_id
from vk.exceptions import APIException
from vk.keyboards import ButtonColor
from vk.keyboards import ButtonType
from vk.keyboards import Keyboard
from vk.types import message
from vk.utils import TaskManager


with open("config.toml", "r", encoding="utf-8") as f:
    if "message_text" in os.environ and "token" in os.environ:
        config = dict(os.environ)
        for key, value in toml.load(f).items():
            if key not in config:
                config[key] = value
    else:
        config = toml.load(f)

logging.basicConfig(level=config["logging_level"])

vk = VK(config["token"])
task_manager = TaskManager(vk.loop)
api = vk.get_api()

dp = Dispatcher(vk)

replay_b = int(config["replay_b"])
def adjust_message_text():
    message_text = config["message_text"].encode()
    if int(config["replay_message"]):
        if len(message_text) < replay_b:
            message_text = message_text * int(replay_b / len(message_text))
        
    config["message_text"] = message_text.decode()


async def apply_required_settings(group_id: int):
    await vk.api_request(
        "groups.setSettings",
        {
            "group_id": group_id,
            "messages": 1,
            "bots_capabilities": 1,
            "bots_add_to_chat": 1,
        },
    )
    await vk.api_request(
        "groups.setLongPollSettings",
        {"group_id": group_id, "enabled": 1, "api_version": "5.103", "message_new": 1},
    )

call_bot_text = "[" + config["call_bot_id_group"] + "|" + config["call_bot_custom_name"] + "]" + config["call_bot_additional_text"]

@dp.message_handler(chat_action = message.Action.chat_invite_user)
@dp.message_handler(text = call_bot_text)
async def chat_invite_user(msg: types.Message, _):
    logging.info(f"Started raiding {msg.peer_id}.")
    sent_message_count = 0
    while True:
        try:
            keyboard = Keyboard(one_time=False)
            for row in range(0, 10):
                button_main_colors = deque(
                    [
                        ButtonColor.POSITIVE,
                        ButtonColor.NEGATIVE,
                        ButtonColor.SECONDARY,
                        ButtonColor.PRIMARY,
                    ]
                )
                button_colors = deque(
                    [
                        button_main_colors[int(config["button_color1"])],
                        button_main_colors[int(config["button_color2"])],
                        button_main_colors[int(config["button_color3"])],
                        button_main_colors[int(config["button_color4"])],
                    ]
                )
                button_colors.rotate(sent_message_count % len(button_colors))
                for button in range(0, 4):
                    keyboard.add_text_button(
                        config["buttons_text"], 
                        color=button_colors[button],
                        payload=None
                    )
                if row != 9:
                    keyboard.add_row()
            if int(config["buttons_enable"]):
                keyboard_switch = keyboard.get_keyboard()
            else:
                keyboard_switch = ""
            await api.messages.send(
                random_id=random.getrandbits(31) * random.choice([-1, 1]),
                peer_id=msg.peer_id,
                message=config["message_text"],
                attachment=config["attachment"],
                keyboard=keyboard_switch,
            )
            sent_message_count += 1
            await asyncio.sleep(float(config["delay"]))
            if sent_message_count == int(config["stop_sending_messages_by_counter"]):
                break
        except APIException as e:
            logging.info(f"Stopped raiding {msg.peer_id}. Reason: {e}")
            if int(config["kill_bot"]):
                break
            else:
                await asyncio.sleep(float(config["delay_kill"]))


async def run():
    group_id = await get_group_id(vk)
    await apply_required_settings(group_id)
    adjust_message_text()
    dp.run_polling(group_id)


if __name__ == "__main__":
    task_manager.add_task(run)
    task_manager.run(auto_reload=True)
