# -*- coding:utf-8 -*-
from encodings import utf_8
from telegram import Update
# pip uninstall python-telegram-bot telegram
# pip install python-telegram-bot --upgrade
# https://github.com/python-telegram-bot/python-telegram-bot/wiki
from telegram.ext import CallbackContext
from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, Filters
import pytz
import redis
import json
import d_chat
import d_chatcount
import d_gag
import d_verify
import d_ping
import hashlib
import time
import datetime

print('正在初始化...')
starttime = datetime.datetime.now()

c_TGTOKEN = '*:*-*'
c_REDIS = ['127.0.0.1', 6379, '*']
c_SUPERMGRID = []
c_REDISDB = [10, 11]  # 配置庫
c_CHAR: list[list[str]] = [
    ['呜', '哈', '啊', '唔', '嗯', '呃', '哦', '嗷', '呕', '噢', '喔'], ['！', '？', '…', '，']]
c_CHARALL: list[str] = c_CHAR[0] + c_CHAR[1]
c_GAGADD = [3, 5]  # 每次增加多少

updater = Updater(token=c_TGTOKEN, use_context=True)
dispatcher = updater.dispatcher
jobQueue = updater.job_queue
oldDay = -1

# Redis
redisPool0: redis.ConnectionPool = redis.ConnectionPool(
    host=c_REDIS[0], port=c_REDIS[1], password=c_REDIS[2], db=c_REDISDB[0])
redisPool1: redis.ConnectionPool = redis.ConnectionPool(
    host=c_REDIS[0], port=c_REDIS[1], password=c_REDIS[2], db=c_REDISDB[1])


def ignoreMessage(msg: str):
    """服務啟動前幾秒拋棄積壓訊息"""
    endtime = datetime.datetime.now()
    runsec: int = (endtime - starttime).seconds
    if (runsec < 5):
        print('忽略消息 '+msg)
        return True
    return False


def isPermission(chatID: int, chatTitle: str) -> bool:
    """檢查該會話是否有許可權使用此機器人"""
    title = ''
    if chatTitle != None:
        title = chatTitle
    if ignoreMessage(str(chatID) + ' ' + title):
        return False
    redisConnect = redis.Redis(connection_pool=redisPool0)
    rediskey = 'can_' + str(chatID)
    passInfo = redisConnect.get(rediskey)
    redisConnect.close()
    if passInfo != None:
        passInfoStr: str = passInfo.decode()
        passInfoArr: list[str] = passInfoStr.split(";")
        if len(passInfoArr) > 0 and passInfoArr[0] == '1':
            return True
    print('不能提供服务 (' + str(chatID) + ') '+title)
    return False


def start(update: Update, context: CallbackContext):
    """響應 /start"""
    fromUser: str = update.message.from_user.username
    text: str = '你好， '+fromUser+' ！\n我只为雅诗指定的群组提供服务。'
    print(text)
    context.bot.send_message(chat_id=update.effective_chat.id, text=text)


start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)


def timing(context: CallbackContext):
    """每幾秒觸發一次"""
    global oldDay
    t = datetime.datetime.now(pytz.timezone('Asia/Shanghai'))
    d_verify.timeChk(context, redisPool0)
    if t.hour == 0 and t.minute == 0 and oldDay != t.day:
        oldDay = t.day
        d_chatcount.sendNewDay(context, redisConnect)
    redisConnect.close()
    # context.bot.send_message(chat_id='@YOUR CHANELL ID',text='job executed')


jobQueue.run_repeating(timing, interval=5.0, first=5.0)


def echo(update: Update, context: CallbackContext):
    """收到的所有非命令文字訊息"""
    print(update)
    if update == None or update.message == None or update.message.chat == None or update.message.from_user == None or update.message.from_user.username == None or update.message.from_user.is_bot == None or update.message.from_user.is_bot:
        return
    if update.message.from_user.id in c_SUPERMGRID:
        cmdTextArr: str = update.message.text.split(';;')
        if len(cmdTextArr) >= 3 and cmdTextArr[0] == 'msg':
            context.bot.send_message(chat_id=int(
                cmdTextArr[1]), text=cmdTextArr[2])
            return
    if isPermission(update.message.chat.id, update.message.chat.title) == False:
        print('N3')
        return
    text: str = update.message.text
    if len(text) == 0 or text[0] == '/':
        print('N4')
        return
    if d_verify.chatChk(update, context, redisPool0):
        print('N5')
        return
    if d_gag.chk(update, context, redisPool0, c_CHAR):
        print('N6')
        return
    d_chatcount.updateCount(update, redisPool0)
    print('777')
    d_chat.chat(update, context, redisPool1)


redisConnect = redis.Redis(connection_pool=redisPool0)
d_chatcount.sendNewDay(None, redisConnect)
redisConnect.close()


def new_member(update, context):
    """新成員加入"""
    if update.message.chat == None or isPermission(update.message.chat.id, update.message.chat.title) == False:
        return
    d_verify.welcome(update, context, redisPool0)


echoHandler = MessageHandler(Filters.text & (
    ~Filters.command), echo, pass_job_queue=True)
dispatcher.add_handler(echoHandler)
newMemberHandler = MessageHandler(
    Filters.status_update.new_chat_members, new_member)
updater.dispatcher.add_handler(newMemberHandler)


def gag(update: Update, context: CallbackContext):
    """為他人佩戴口球"""
    if update.message.chat == None or update.message.chat.type == None or isPermission(update.message.chat.id, update.message.chat.title) == False:
        return
    # group, supergroup, private, channel
    if update.message.chat.type == 'private' and len(context.args) > 0 and context.args[0] == 'help':
        d_gag.add(update, context, redisPool0, c_CHAR)
        return
    if isPermission(update.message.chat.id, update.message.chat.title) == False:
        return
    d_gag.add(update, context, redisPool0, c_CHAR)


caps_handler = CommandHandler('gag', gag)
dispatcher.add_handler(caps_handler)


def about(update: Update, context: CallbackContext):
    """幫助"""
    if update.message.chat == None or update.message.chat.type == None:
        return
    if update.message.chat.type != 'private':
        alert = '点此了解：\nhttps://t.me/rbq_ch_bot_ch/3'
        context.bot.send_message(chat_id=update.effective_chat.id, text=alert)
        print(update.effective_chat.id, update.effective_chat.title,
              update.message.from_user.id, update.message.from_user.username, alert)
        return
    f = open('help_about.txt', 'r', encoding='utf_8')
    txt = f.read()
    f.close()
    # if hashlib.md5(txt.encode()).hexdigest() != 'dcf0894f267288695a2273924a2c3f57':
    #     txt = '文件保护功能检测到错误，请联系实例维护者。'
    context.bot.send_message(chat_id=update.effective_chat.id, text=txt)


caps_handler = CommandHandler('about', about)
dispatcher.add_handler(caps_handler)


def rbqpoint(update: Update, context: CallbackContext):
    """絨度值查詢"""
    if update == None or update.message == None or update.message.from_user == None or update.message.from_user.username == None or isPermission(update.message.chat.id, update.message.chat.title) == False:
        return
    user: str = '@'+update.message.from_user.username
    fromUser = user
    if len(context.args) == 1 and len(context.args[0]) > 0 and context.args[0][0] == '@':
        user = context.args[0]
    redisConnect = redis.Redis(connection_pool=redisPool0)
    rediskey: str = 'rpt_' + str(user)
    point = 0
    rpointInfo = redisConnect.get(rediskey)
    redisConnect.close()
    if rpointInfo != None and len(rpointInfo) > 0:
        rpointInfo = rpointInfo.decode()
        point = int(rpointInfo)
    alert = ''
    if fromUser != user:
        alert += fromUser+' 所查询的 '
    alert += user+' 的「绒度」是 '+str(point)+' 。\n该「绒度」值在本 bot 所在的群组中通用。'
    if point == 0:
        if fromUser != user:
            alert += '\n你要帮助 '+user+' 成为绒布球吗？'
        else:
            alert += '\n第一次使用吗？要了解绒度计算方式和玩法可以输入 `/gag help` 。'
    elif point <= 10:
        alert += '\n是个可爱的萌新绒布球呢。'
    elif point <= 100:
        alert += '\n是个很有潜力的绒布球呢。'
    elif point <= 500:
        alert += '\n是个合格的绒布球呢。'
    elif point <= 1000:
        alert += '\n是个大号绒布球呢。'
    elif point <= 3000:
        alert += '\n是个巨型绒布球！'
    elif point <= 5000:
        alert += '\n是 个 超 级 绒 布 球 ！'
    elif point <= 10000:
        alert += '\n已 经 是 究 极 绒 布 球 了 ！'
    elif point > 10000:
        alert += '\n本 群 元 老 级 绒 布 球 ！'
    print(update.effective_chat.id, update.effective_chat.title,
          update.message.from_user.id, update.message.from_user.username, alert)
    context.bot.send_message(
        chat_id=update.effective_chat.id, text=alert)


caps_handler = CommandHandler('rbqpoint', rbqpoint)
dispatcher.add_handler(caps_handler)


def ping(update: Update, context: CallbackContext):
    permission: bool = isPermission(
        update.message.chat.id, update.message.chat.title)
    if update.message.chat == None or permission == False:
        return
    d_ping.ping(update, context, starttime, permission, redisPool0, redisPool1)


caps_handler = CommandHandler('ping', ping)
dispatcher.add_handler(caps_handler)


def verify(update: Update, context: CallbackContext):
    if update.message.chat == None or isPermission(update.message.chat.id, update.message.chat.title) == False:
        return
    d_verify.verify(update, context, redisPool0)


caps_handler = CommandHandler('verify', verify)
dispatcher.add_handler(caps_handler)

print('初始化完成。')

updater.start_polling()
updater.idle()

