from nonebot import on_notice, require
from nonebot.plugin.on import on_command
from nonebot.adapters.onebot.v11 import (
    GROUP,
    Bot,
    GroupMessageEvent,
    GroupDecreaseNoticeEvent,
    Message,
    MessageSegment,
    )
from nonebot.params import CommandArg, ArgStr
import nonebot
import os
import random
import asyncio
import time
from models.bag_user import BagUser
from models.group_member_info import GroupInfoUser
from datetime import datetime,date,timedelta
import pytz
from nonebot import require
require("nonebot_plugin_htmlrender")
from nonebot_plugin_htmlrender import md_to_pic
from .model import UsersInfo,BayUsers
from .utils import *
from utils.utils import scheduler

__zx_plugin_name__ = "群友市场"
__plugin_usage__ = """
usage:
    发送群友市场 查看群友交易市场，
    发送购买群友+@群友 可买下群友帮你打工
    发送我的群友查看 我当前已经购买的群友，
    发送一键打工 可让你的所有群友为你打工（没有群友就自己打工）
        
""".strip()
__plugin_des__ = "群友交易市场"
__plugin_cmd__ = ["群友市场", "购买群友"]
__plugin_type__ = ("群内小游戏",)
__plugin_settings__ = {
    "level": 5,
    "default_status": True,
    "limit_superuser": False,
    "cmd": __plugin_cmd__,
}

__plugin_cd_limit__ = {
    "cd":10,
    "rst": "每十秒只能操作一次..."
}

today = date.today()

usershop = on_command("群友市场",aliases = {"查看群友市场"}, permission=GROUP, priority = 5, block = True)

@usershop.handle()
async def _(bot:Bot, event: GroupMessageEvent):
    group_id = event.group_id
    user_id = event.user_id
    ulist:dict[int, int]={}
    ulist = await UsersInfo.get_all_user(group_id)
    if ulist:
        msg=f'### 群友市场（最多显示80个，未出现在市场里的除了显示不下的都只值100）\n' \
            '|名称|qq号|身价|主人|\n' \
            '| --- | --- | --- | --- |\n'
        for qq,p in ulist.items():
            if user_ := await GroupInfoUser.get_or_none(user_id=qq, group_id=group_id):
                user_name = user_.user_name
            if user_ := await BayUsers.get_or_none(group_id=group_id,auser_qq=qq):
                if usern := await GroupInfoUser.get_or_none(user_id=user_.muser_qq, group_id=group_id):
                    user_name1 = usern.user_name
                umaster = user_name1
                msg += f"|<img width='20%' src='http://q1.qlogo.cn/g?b=qq&nk={qq}&s=100'/>  {user_name}|{qq}|{p}|<img width='20%' src='http://q1.qlogo.cn/g?b=qq&nk={usern.user_qq}&s=100'/>  {umaster}|\n"
            else:
                umaster="无"
                msg += f"|<img width='20%' src='http://q1.qlogo.cn/g?b=qq&nk={qq}&s=100'/>  {user_name}|{qq}|{p}|{umaster}|\n"

        output = await md_to_pic(md=msg)
        await usershop.finish(MessageSegment.image(output), at_sender=True)
    else:
        await usershop.finish("群友市场空无一人（所有人都只值100）", at_sender=True)



myuser = on_command("我的群友",aliases = {"查看我的群友"} , permission = GROUP, priority = 5, block = True)

@myuser.handle()
async def _(bot:Bot, event: GroupMessageEvent):
    group_id = event.group_id
    user_id = event.user_id
    ulist:dict[int, int]={}
    ulist = await UsersInfo.get_all_auser(user_id,group_id)
    if ulist:
        msg=f'### 我的群友（最多显示80个）\n' \
            '|名称|qq号|身价|\n' \
            '| --- | --- | --- |\n'
        for qq,p in ulist.items():
            if user_ := await GroupInfoUser.get_or_none(user_id=qq, group_id=group_id):
                user_name = user_.user_name
            msg += f"|<img width='20%' src='http://q1.qlogo.cn/g?b=qq&nk={qq}&s=100'/>  {user_name}|{qq}|{p}|\n"

        output = await md_to_pic(md=msg)
        await myuser.finish(MessageSegment.image(output), at_sender=True)
    else:
        await myuser.finish("你还没有购买群友", at_sender=True)

# 查看娶群友卡池

buyuser = on_command("购买群友", permission = GROUP, priority = 5, block = True)

@buyuser.handle()
async def _(bot:Bot, event: GroupMessageEvent, msgs: Message = CommandArg()):
    group_id = event.group_id
    user_id = event.user_id
    at = get_message_at(event.json())
    atqq = msgs.extract_plain_text().strip()
    try:
        if user_ := await GroupInfoUser.get_or_none(user_id=at[0], group_id=group_id):
            user_name = user_.user_name
            qq=at[0]
        else:
            await buyuser.finish("群里好像没有这个人捏~", at_sender=True)
    except:
        try:
            if user_ := await GroupInfoUser.get_or_none(user_id=atqq, group_id=group_id):
                user_name = user_.user_name
                qq=atqq
            else:
                await buyuser.finish("群里好像没有这个人捏~", at_sender=True)     
     
        except ValueError:
            await buyuser.finish("不可以购买我捏~", at_sender=True) 
            
    if str(qq) == str(user_id):
        await buyuser.finish("不可以购买自己捏~", at_sender=True)
        return
    if str(qq) == str(bot.self_id):
        await buyuser.finish("不可以购买我捏~", at_sender=True)
        return
        
    auser, is_create = await UsersInfo.get_or_create(user_qq=qq, group_id=group_id)
    user = await BayUsers.get_or_none(group_id=group_id,auser_qq=qq)
    if not user:
        #第一次被买，钱给黑奴
        if await BagUser.get_gold(user_id,group_id) < auser.body_price:
            await buyuser.finish(f"你买不起！需要{auser.body_price}金币", at_sender=True)
            return
        m = await UsersInfo.add_user(user_id,group_id,qq)
        await BagUser.add_gold(qq,group_id,m)
        await BagUser.spend_gold(user_id,group_id,m)
        a = await BagUser.get_gold(qq,group_id)
        u = await BagUser.get_gold(user_id,group_id)
        msg=f"成功购买了{user_name}！花费了{m}金币，还剩{u}金币\n{user_name}获得了{m}金币，现在拥有{a}金币，身价上涨{m}->{m+20}"
        output = text_to_png(msg)
        if not is_create:
            await buyuser.send("前主人已失踪，金币付给奴隶", at_sender=True)
        await buyuser.finish(MessageSegment.image(output), at_sender=True)
    else:
        #被买走，钱给前主人
        auser = await UsersInfo.get_or_none(group_id=group_id,user_qq=qq)
        if await BagUser.get_gold(user_id,group_id) < auser.body_price:
            await buyuser.finish(f"你买不起！需要{auser.body_price}金币", at_sender=True)
            return
        if user_ := await GroupInfoUser.get_or_none(user_id=user.muser_qq, group_id=group_id):
            user_name2 = user_.user_name
        m = await UsersInfo.add_user(user_id,group_id,qq)
        if not m:
            await buyuser.finish("你已经是他的主人了！", at_sender=True)
            return
        else:
            await BagUser.add_gold(user.muser_qq,group_id,m)
            await BagUser.spend_gold(user_id,group_id,m)
            await BagUser.add_gold(qq,group_id,m/10)
            a = await BagUser.get_gold(qq,group_id)
            u = await BagUser.get_gold(user_id,group_id)
            u2 = await BagUser.get_gold(user.muser_qq,group_id)
            msg=f"成功从{user_name2}那里购买了{user_name}！花费了{m}金币，还剩{u}金币\n{user_name2}获得了{m}金币，现在拥有{u2}金币\n{user_name}额外获得了{m/10}金币，现在拥有{a}金币，身价上涨{m}->{m+20}"
            output = text_to_png(msg)
            await buyuser.finish(MessageSegment.image(output), at_sender=True)

work = on_command("一键打工", permission = GROUP, priority = 5, block = True)

@work.handle()
async def _(bot:Bot, event: GroupMessageEvent):
    present = datetime.now(pytz.timezone('Asia/Shanghai'))
    group_id = event.group_id
    user_id = event.user_id
    user, is_create = await UsersInfo.get_or_create(user_qq=user_id, group_id=group_id)
    print(user.checkin_time_last)
    print(present)
    if user.checkin_time_last + timedelta(hours=4) >= present:
        await work.finish("最近四小时内已经打过工了!", at_sender=True)
        return
    ulist = await UsersInfo.get_all_ausers(user_id,group_id)
    if not ulist:
        #没有黑奴，只能自己去打工
        await UsersInfo.work(user_id,group_id)
        gold = random.randint(10, 40)
        m = await UsersInfo.get_or_none(user_qq=user_id, group_id=group_id)
        gold=gold+ random.randint(m.body_price/10, m.body_price/5)
        await BagUser.add_gold(user_id,group_id,gold)
        u = await BagUser.get_gold(user_id,group_id)
        NICKNAME="【你】"
        msg=(
            random.choice(
                [
                    f"{NICKNAME}参加了网红主播的不要笑挑战。获得收入{str(gold)}金币",
                    f"{NICKNAME}在闲鱼上卖东西，获得收入{str(gold)}金币",
                    f"{NICKNAME}去在大街上发小传单，获得收入{str(gold)}金币",
                    f"{NICKNAME}参加漫展，帮著名画师毛玉牛乳兜售新作，获得收入{str(gold)}金币",
                    f"{NICKNAME}在美食街出售鸡你太美飞饼，虽然把饼甩飞了，但是围观群众纷纷购买鸡哥飞饼，获得收入{str(gold)}金币",
                    f"{NICKNAME}偷渡到美国在中餐馆洗盘子，获得收入{str(gold)}金币",
                    f"{NICKNAME}去黑煤窑挖煤，获得收入{str(gold)}金币",
                    f"{NICKNAME}去横店当太君群演，被八路手撕了20次导演才说咔，获得收入{str(gold)}金币",
                    f"{NICKNAME}去参加银趴服务别人，获得收入{str(gold)}金币",
                    f"{NICKNAME}去拍摄小电影，获得收入{str(gold)}金币",
                    f"{NICKNAME}去b站做审核员，看了十二小时旋转鸡块，获得收入{str(gold)}金币",
                ]
            )
        )
        msg=msg+f"\n当前共有{u}金币"
        msg="你没有群友只能自己去打工\n"+msg
        output = text_to_png(msg)
        await work.finish(MessageSegment.image(output), at_sender=True)
    else:
        #派出所有黑奴去干活
        await UsersInfo.work(user_id,group_id)
        golds=0
        msgs="你派出了所有群友去打工\n"
        for qq,p in ulist.items():
            if user_ := await GroupInfoUser.get_or_none(user_id=qq, group_id=group_id):
                NICKNAME = f"【{user_.user_name}】"
            gold = random.randint(10, 40)
            gold=gold+ random.randint(p/10, p/5)
            
            #10%概率没钱
            ran=random.randint(1,10)
            if ran != 6:
                msg=(
                    random.choice(
                        [
                            f"{NICKNAME}参加了网红主播的不要笑挑战。获得收入{str(gold)}金币",
                            f"{NICKNAME}在闲鱼上卖东西，获得收入{str(gold)}金币",
                            f"{NICKNAME}去在大街上发小传单，获得收入{str(gold)}金币",
                            f"{NICKNAME}参加漫展，帮著名画师毛玉牛乳兜售新作，获得收入{str(gold)}金币",
                            f"{NICKNAME}在美食街出售鸡你太美飞饼，虽然把饼甩飞了，但是围观群众纷纷购买鸡哥飞饼，获得收入{str(gold)}金币",
                            f"{NICKNAME}偷渡到美国在中餐馆洗盘子，获得收入{str(gold)}金币",
                            f"{NICKNAME}去黑煤窑挖煤，获得收入{str(gold)}金币",
                            f"{NICKNAME}去横店当太君群演，被八路手撕了20次导演才说咔，获得收入{str(gold)}金币",
                            f"{NICKNAME}去参加银趴服务别人，获得收入{str(gold)}金币",
                            f"{NICKNAME}去拍摄小电影，获得收入{str(gold)}金币",
                            f"{NICKNAME}去b站做审核员，看了十二小时旋转鸡块，获得收入{str(gold)}金币",
                        ]
                    )
                )
                golds=golds+gold
            else:
                m = await UsersInfo.add_body_price(group_id,qq)
                msg=(
                    random.choice(
                        [
                            f"{NICKNAME}参加了网红主播的不要笑挑战。结果刚上场就蚌不住了，一分没挣着,{NICKNAME}身价下降{m+20}->{m}",
                            f"{NICKNAME}在闲鱼上卖东西，结果完全卖不出去，一分没挣着,{NICKNAME}身价下降{m+20}->{m}",
                            f"{NICKNAME}去在大街上发小传单，没有一个人要传单，一分没挣着,{NICKNAME}身价下降{m+20}->{m}",
                            f"{NICKNAME}参加漫展，帮著名画师毛玉牛乳兜售新作，结果忍不住在展台冲了出来，被人家赶了出去，一分没挣着,{NICKNAME}身价下降{m+20}->{m}",
                            f"{NICKNAME}在美食街出售鸡你太美飞饼，结果把饼甩飞了，围观群众都散了，一分没挣着,{NICKNAME}身价下降{m+20}->{m}",
                            f"{NICKNAME}偷渡到美国在中餐馆洗盘子，结果一个黑人逃进了中餐馆，后面一个警察在后面追着扫射，{NICKNAME}害怕的跑了出来，一分没挣着,{NICKNAME}身价下降{m+20}->{m}",
                            f"{NICKNAME}去黑煤窑挖煤，但{NICKNAME}没有力气完全挖不动，一分没挣着还被骂了",
                            f"{NICKNAME}去横店当太君群演，被八路手撕了20次导演还说不行，说{NICKNAME}演的不好就把你赶出去了，一分没挣着,{NICKNAME}身价下降{m+20}->{m}",
                            f"{NICKNAME}去参加银趴服务别人，别人说{NICKNAME}把他弄疼了，就把{NICKNAME}赶出去了，一分没挣着还被骂了,{NICKNAME}身价下降{m+20}->{m}",
                            f"{NICKNAME}去拍摄小电影，因为没有经验某些姿势老做不好,把{NICKNAME}赶了出去，一分没挣着还被骂了,{NICKNAME}身价下降{m+20}->{m}"
                            f"{NICKNAME}去b站做审核员，要看十二小时旋转鸡块，{NICKNAME}以为没事随便看两眼就给过了，结果被举报中间掺了毛玉牛乳最新画作，一分没挣着被开除了,{NICKNAME}身价下降{m+20}->{m}",
                        ]
                    )
                )                
            msgs=msgs+msg+"\n"
        await BagUser.add_gold(user_id,group_id,golds)
        u = await BagUser.get_gold(user_id,group_id)
        if len(msgs.splitlines())>80:
            s=""
            for i in msgs.splitlines()[:80]:
                s=s+i+"\n"
            msgs=s+"......\n"
        msgs=msgs+f"你总共获取{golds}金币，当前共有{u}金币"
        output = text_to_png(msgs)
        await work.finish(MessageSegment.image(output), at_sender=True)
        
#退群处理        
group_decrease_handle = on_notice(priority=1, block=False)

@group_decrease_handle.handle()
async def _(bot: Bot, event: GroupDecreaseNoticeEvent):
    group_id = event.group_id
    user_id = event.user_id
    y = await UsersInfo.remove_user(user_id,group_id)
    print(f"已删除{user_id}")

@scheduler.scheduled_job(
    "cron",
    hour=12,
    minute=0,
)   
async def auto_update_member_info():
    buylist = await BayUsers.all()
    for buy in buylist:
        _group_user_list = await GroupInfoUser.filter(group_id=buy.group_id).all()
        _userids=[]
        for user_info in _group_user_list:
            _userids.append(user_info.user_id)
        if not buy.auser_qq in _userids:
            await UsersInfo.remove_user(buy.auser_qq,buy.group_id)
        elif not buy.muser_qq in _userids:
            await UsersInfo.remove_user(buy.muser_qq,buy.group_id)
    print("群友市场更新完成")
    
up = on_command("更新群友市场",aliases = {"更新群友市场"}, permission=GROUP, priority = 5, block = True)

@up.handle()            
async def update_member_info(bot:Bot, event: GroupMessageEvent):
    group_id = event.group_id
    try:
        buylist = await BayUsers.filter(group_id=group_id).all()
        _group_user_list = await GroupInfoUser.filter(group_id=group_id).all()
        _userids=[]
        i=0
        for user_info in _group_user_list:
            _userids.append(user_info.user_id)
        for buy in buylist:
            if not buy.auser_qq in _userids:
                await UsersInfo.remove_user(buy.auser_qq,buy.group_id)
                i=i+1
            elif not buy.muser_qq in _userids:
                await UsersInfo.remove_user(buy.muser_qq,buy.group_id)
                i=i+1
    except Exception as e:
        await up.finish(f"群友市场更新失败{e}")
    await up.send(f"群友市场更新完成,共删除{i}条数据")
