import io
import hashlib
import asyncio

from nonebot_plugin_imageutils import BuildImage,Text2Image

try:
    import ujson as json
except ModuleNotFoundError:
    import json


def text_to_png(msg):
    '''
    文字转png
    '''
    output = io.BytesIO()
    Text2Image.from_text(msg,50,spacing = 10).to_image("white",(20,20)).save(output, format="png")
    return output

def bbcode_to_png(msg, spacing: int = 10):
    '''
    bbcode文字转png
    '''
    output = io.BytesIO()
    Text2Image.from_bbcode_text(msg, 50, spacing = spacing).to_image("white", (20,20)).save(output, format="png")
    return output

def get_message_at(data: str) -> list:
    '''
    获取at列表
    :param data: event.json()
    '''
    qq_list = []
    data = json.loads(data)
    try:
        for msg in data['message']:
            if msg['type'] == 'at':
                qq_list.append(int(msg['data']['qq']))
        return qq_list
    except Exception:
        return []
