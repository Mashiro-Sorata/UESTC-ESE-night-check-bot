# import nonebot
from nonebot import get_driver

from .config import Config

from nonebot import on_command, on_keyword
from nonebot.rule import to_me, regex, Rule
from nonebot.log import logger

from .model import database
import time
import asyncio
from threading import Thread, Lock
import re
import requests
import win32api

import httpx
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


global_config = get_driver().config
config = Config(**global_config.dict())

# 自动晚点名标志位,禁止晚点名中添加用户的操作
autotask_flag = False

today_date = time.strftime('%m%d', time.localtime(time.time() - 24*3600))

# 防止竞争,给晚点名线程加锁(禁用添加用户操作后,这一步也许多余了)
task_locker = Lock()

# logger.debug(database.getall())

# 重启cqhttp状态位, True为重启中,若更改代码需要手动重置为False,否则无法完成重启
reboot_flag = False


# 判断消息是否来自于QQ号为group_id的群
async def is_in_group(event, group_id):
    return True if hasattr(event, 'group_id') and event.group_id == group_id else False

# 自定义规则: 判断消息是否为用户群内发送
async def rule_checker_in_user_group(bot, event, state):
    if hasattr(event, 'group_id'):
        if event.group_id == config.user_group_id:
            return True
    return False

# 自定义规则: 判断消息是否为设置中的"管理员"所发(注:非QQ群的管理员)
async def is_admin(bot, event, state):
    if event.user_id == config.admin_id:
        return True
    return False

# 检查用户输入的选项串是否在config.second_choices_pool内
async def check_choices(choices):
    ret = config.second_choices_pool
    for each in choices:
        try:
            ret = ret.get(each)[0]
        except TypeError:
            return False
    if ret == {}:
        return True
    else:
        return False

# 得到用户输入的数字选项串的选项内容
def get_choices_name(choices):
    ret = config.second_choices_pool
    for each in choices:
        try:
            yield ret.get(each)[1]
            ret = ret.get(each)[0]
        except TypeError:
            return

# 重启cqhttp,通过Bat文件实现
def restart_cqhttp(flag=config.auto_restart):
    global reboot_flag
    if flag and not reboot_flag:
        win32api.ShellExecute(0, 'open', r'cqhttp-restart.bat', '','',1)
        reboot_flag = True

# Bot通过event发送消息,可@发送者,带风控错误处理（网络错误之类的由于Bot不会主动发送消息,并不会触发）
async def bot_send(bot, event, msg, at_sender=False):
    global reboot_flag
    for _ in range(config.max_try):
        try:
            await bot.send(event, msg, at_sender=at_sender)
            reboot_flag = False
            return
        except Exception as e:
            restart_cqhttp()
            await asyncio.sleep(config.try_sleep)
            logger.debug(e)
    reboot_flag = False

# Bot调用api,带风控错误处理(这里主要用来在通知群收到点名通知后响应,在用户群内发送消息)
async def bot_call_api(bot, cmd, **data):
    global reboot_flag
    for _ in range(config.max_try):
        try:
            await bot.call_api(cmd, **data)
            reboot_flag = False
            return
        except Exception as e:
            restart_cqhttp()
            await asyncio.sleep(config.try_sleep)
            logger.debug(e)
    reboot_flag = False




# 测试方便,最后添加rule=to_me()
# check = on_command('check', aliases=set(('晚点名', '点名')), rule=Rule(rule_checker_in_user_group), priority=1)

# 晚点名服务群
check = on_command('check', aliases=set(('晚点名', '点名')), priority=1)

# 晚点名通知群
notice = on_keyword(set(('晚点名',)), rule=regex(r'http[s]?://[\S]*'), priority=1)

# 重启go-cqhttp服务
reboot = on_command('ctrl', aliases=set(('控制', 'control')), rule=Rule(is_admin), priority=1)


@reboot.handle()
async def handle_reboot(bot, event, state):
    args = str(event.get_message()).strip().split()
    if args and args[0] in set(('reboot', 'restart', '重启')):
        restart_cqhttp(True)
        await asyncio.sleep(config.try_sleep)
        await bot_send(bot, event, 'QQBot已重新上线...')
        return
    await bot_send(bot, event, 'QQBot在线中...')
    
    
        


@notice.handle()
async def handle_notice(bot, event, state):
    global today_date
    if await is_in_group(event, config.target_group_id) and not autotask_flag:
        state['url'] = re.findall(r'http[s]?://[\S]*', str(event.message))[0]
        async with httpx.AsyncClient() as client:
            r = await client.get(state['url'])
        date = re.search(r'电子学院晚点名([\d]{4})', r.text).group(1)
        if today_date != date:
            today_date = date
            await autotask(bot, state)
        else:
            logger.debug('晚点名已完成')


@check.handle()
async def handle_check(bot, event, state):
    if not await is_in_group(event, config.user_group_id):
        if not await is_in_group(event, config.target_group_id):
            await bot_send(bot, event, '请在用户群内完成此操作！')
        return
    args = str(event.get_message()).strip().split()
    state['args'] = args if args else ['help']
    state['user_data'] = database.get(str(event.user_id))
    await cmd_handle(bot, event, state)


async def cmd_handle(bot, event, state):
    # bind/update 命令
    if state['args'][0] in config.cmd_dict['bind']:
        await bind(bot, event, state)
    elif state['args'][0] in config.cmd_dict['status']:
        await status(bot, event, state)
    elif state['args'][0] in config.cmd_dict['delete']:
        await delete(bot, event, state)
    elif state['args'][0] in config.cmd_dict['help']:
        await _help(bot, event)
    else:
        await bot_send(bot, event, '无效命令！', at_sender=True)


# 绑定账号信息
async def bind(bot, event, state):
    # 检查输入是否规范
    if len(state['args']) > 1 and state['args'][1].isnumeric():
        bind_args = state['args'] + [None for _ in range(4 - len(state['args']))]
        # 检查选项是否正确(保证晚点名成功)
        if bind_args[2] is not None:
            if bind_args[2].isnumeric():
                if not bind_args[2][0] in '123' or not await check_choices(bind_args[2][1:]):
                    await bot_send(bot, event, '无效选项串，请查看说明后重试！', at_sender=True)
                    return None
            else:
                if state['user_data']:
                    await bot_send(bot, event, '恭喜您！信息更新成功！', at_sender=True)
                else:
                    await bot_send(bot, event, '恭喜您！信息绑定成功！', at_sender=True)
                database.update(str(event.user_id), bind_args[1], None, bind_args[2])
                logger.debug(database.getall())
                return None
        if state['user_data']:
            await bot_send(bot, event, '恭喜您！信息更新成功！', at_sender=True)
        else:
            await bot_send(bot, event, '恭喜您！信息绑定成功！', at_sender=True)
        database.update(str(event.user_id), bind_args[1], bind_args[2], bind_args[3])
    else:
        await bot_send(bot, event, '学号错误，绑定失败！', at_sender=True)


# 检查账号打卡情况
async def status(bot, event, state):
    if state['user_data']:
        if time.strftime('%m%d', time.localtime(time.time())) == state['user_data']['lasttime']:
            status_str = '\n已完成晚点名！ '
        else:
            status_str = '\n晚点名未完成！ '
        status_str += '\n%s\n%s\n%s' % (
            state['user_data']['stuid'],
            state['user_data']['choices'],
            state['user_data']['address'] if len(state['user_data']['address']) < 11 else (state['user_data']['address'][:10] + '...'))
        await bot_send(bot, event, str(status_str), at_sender=True)
    else:
        await bot_send(bot, event, '您还未加入晚点名服务！', at_sender=True)


# 删除用户
async def delete(bot, event, state):
    if state['user_data']:
        database.delete(str(event.user_id))
        await bot_send(bot, event, '已成功删除绑定信息！', at_sender=True)
    else:
        await bot_send(bot, event, '您还未加入晚点名服务！', at_sender=True)


# 查看帮助
async def _help(bot, event):
    await bot_send(bot, event, config.help_str, at_sender=True)


# ================================晚点名服务====================================

# 在用户群内发送消息并@指定用户
def send_group_msg_and_at(uid, msg):
    global reboot_flag
    data = {'group_id': config.user_group_id,
            'message': '[CQ:at,qq=%s]\n%s' % (str(uid), msg)}
    for _ in range(config.max_try):
        try:
            requests.post(config.send_group_msg_url, data, timeout=5)
            reboot_flag = False
            return
        except Exception as e:
            restart_cqhttp()
            time.sleep(config.try_sleep)
            logger.debug(e)
    reboot_flag = False


# 同步检查子进程是否结束
async def thread_check(thread):
    while thread.isAlive():
        await asyncio.sleep(1)

# 晚点名
def night_check(wait, data):
    try:
        # 学号
        stuid_input = wait.until(EC.presence_of_element_located(
            (By.XPATH, '/html/body/div/div[1]/div/form/div[3]/div/div[2]/div/div[2]/div/div/span/input')))
        stuid_input.clear()
        stuid_input.send_keys(data['stuid'])

        # 选择校区
        school = wait.until(EC.presence_of_element_located((By.XPATH,
                                                            '//label/span/span[contains(text(), "%s")]' %
                                                            config.first_choices_pool[data['choices'][0]])))
        school.click()

        # 根据用户的提供的选项串选择
        for choice in get_choices_name(data['choices'][1:]):
            element = wait.until(EC.presence_of_element_located((By.XPATH,
                                                                 '//label/span/span[contains(text(), "%s")]' % choice)))
            element.click()

        # 定位
        position = wait.until(EC.presence_of_element_located(
            (By.XPATH, '/html/body/div/div[1]/div/form/div[3]/div/div[10]/div/div[2]/div/div/span/div/div/button')))
        position.click()

        time.sleep(10)
        position_input = wait.until(EC.presence_of_element_located((By.XPATH,
            '/html/body/div/div[1]/div/form/div[3]/div/div[10]/div/div[2]/div/div/span/div/div/div[2]/div[2]/div/input')))
        position_input.send_keys(data['address'])
        position_submit = wait.until(EC.presence_of_element_located((By.XPATH,
            '/html/body/div/div[1]/div/form/div[3]/div/div[10]/div/div[2]/div/div/span/div/div/div[2]/div[2]/div/button')))
        position_submit.click()
        time.sleep(8)
        # 提交
        submit = wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/div/div[1]/div/form/div[5]/div[1]/button')))
        submit.click()
    except Exception as e:
        logger.debug(e)
        return 3

    # 返回值:
    # 0: 打卡成功
    # 1: 学号错误或已经完成打卡
    # 2: 无法搜索到地址
    try:
        wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/div/div[2]/div[2]/div/div[1]')))
        return 0
    except Exception:
        try:
            wait.until(EC.presence_of_element_located(
                (By.XPATH, '/html/body/div[1]/div[1]/div/form/div[3]/div/div[2]/div/div[2]/div[2]/div')))
            return 1
        except Exception:
            return 2

# 通过得到的url自动完成晚点名服务,子线程函数
def autodo(url):
    global autotask_flag, today_date
    browser = webdriver.Firefox()
    wait = WebDriverWait(browser, 15)
    with task_locker:
        autotask_flag = True
        logger.debug('开始打卡服务！')
        user_data = database.getall()
        for uid in user_data.keys():
            browser.get(url)
            rcode = night_check(wait, user_data[uid])
            if not rcode:
                send_group_msg_and_at(int(uid), '您的晚点名已成功完成！')
                database.update(uid, None, None, None, today_date)
            elif rcode == 1:
                send_group_msg_and_at(int(uid), '您的晚点名失败\n原因: 学号错误或已经完成打卡！')
            elif rcode == 2:
                send_group_msg_and_at(int(uid), '您的晚点名失败\n原因: 未找到绑定的地址！')
            else:
                send_group_msg_and_at(int(uid), '您的晚点名失败\n原因: 未知错误！')

        logger.debug('完成打卡服务！')
        autotask_flag = False
    browser.quit()


async def autotask(bot, state):
    await bot_call_api(bot, 'set_group_whole_ban', **{'group_id': config.user_group_id, 'enable': True})
    await asyncio.sleep(1)
    await bot_call_api(bot, 'send_group_msg', **{'group_id': config.user_group_id,
                                            'message': '检测到晚点名链接！\n群禁言已开启，晚点名即将开始！'})
    # 等待其他服务响应完成
    await asyncio.sleep(5)
    t = Thread(target=autodo, args=(state['url'],))
    t.start()
    await thread_check(t)
    await bot_call_api(bot, 'send_group_msg', **{'group_id': config.user_group_id,
                                            'message': '晚点名已完成！\n群禁言将关闭！'})
    await asyncio.sleep(1)
    await bot_call_api(bot, 'set_group_whole_ban', **{'group_id': config.user_group_id, 'enable': False})
