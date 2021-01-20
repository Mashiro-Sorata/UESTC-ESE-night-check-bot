#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import win32api

import nonebot
from nonebot.adapters.cqhttp import Bot as CQHTTPBot

nonebot.init()
app = nonebot.get_asgi()

driver = nonebot.get_driver()
driver.register_adapter("cqhttp", CQHTTPBot)


nonebot.load_builtin_plugins()
nonebot.load_plugins("qqbot/plugins")


async def send_hello(bot):
    await bot.call_api('send_private_msg', **{'user_id': nonebot.plugin.get_plugin('night_check').module.config.admin_id,
                                        'message': 'QQBot已上线'})

driver.on_bot_connect(send_hello)


win32api.ShellExecute(0, 'open', r'cqhttp-restart.bat', '','',1)

if __name__ == "__main__":
    nonebot.run(app="bot:app")
