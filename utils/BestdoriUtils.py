import asyncio
import datetime
import json
import math
import os
import threading
import time
from functools import wraps
from typing import Tuple

import aiohttp
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from threading import Thread
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from nonebot.log import logger

from utils.ImageUtils import ImageUtils

USE_CACHE = False
JP, EN, TW, CN, KR = 0, 1, 2, 3, 4

class Download(object):
    def __init__(self):
        self.nowthread = 0
        self.maxThread = 32
        self.threadLock = threading.Lock()
        self.headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.67 Safari/537.36 Edg/87.0.664.47',
        'Referer':'https://bestdori.com/',
        'Host':'bestdori.com'
    }
        
    def get_bad_url(self) -> list:
        with open(os.path.abspath(f'./cache/BadUrl.txt'), "r") as file:
            return [line.strip() for line in file.readlines()]

    def download_files(self, url, folder_name, file_name):
        file_path = os.path.abspath(f'./data/{folder_name}/{file_name}')

        if not os.path.exists(os.path.abspath(f'./data/{folder_name}')):
            os.mkdir(os.path.abspath(f'./data/{folder_name}'))

        try:
            data = requests.get(url, headers = self.headers)
            with open(file_path, 'wb') as f:
                f.write(data.content)
                f.close()
            if os.path.getsize(file_path) == 14559:
                os.remove(file_path)
                logger.warning("DOWNLOAD: Bestdori图片缺失 " + url)
                with open(os.path.abspath(f'./cache/BadUrl.txt'), "a") as file:
                    file.write(url + "\n")
            else:
                logger.success("DOWNLOAD: 成功下载 " + url)
            self.nowthread -= 1
        except Exception as e:
            logger.error("DOWNLOAD: ", e)
            self.nowthread -= 1
            return

    def download_cards(self, li, server_dict):
        __url = "https://bestdori.com/assets/{}/characters/resourceset/"

        for res in li:
            # try:
                # 无限循环，检查当前正在运行的线程数量是否达到设定的上限
                # 没有达到则启动新的线程，执行一张立绘图片的下载任务，启动新线程成功后跳出无限循环，否则持续循环下去，直到能够运行新线程位为止
                while 1:
                    # 线程暂停0.01秒，防止执行过快导致的各类问题如崩溃
                    time.sleep(0.05)
                    # 一旦发现有空余则开启下载，否则无限循环等待
                    if 0 <= self.nowthread <= self.maxThread:
                        # 立刻启动新线程，调用真正的下载方法，传入图片所属id和图片类型，完整下载
                        url = f'{__url.format(server_dict[res[:9]])}{res[:9]}_rip/{res[10:]}'
                        if url not in self.get_bad_url():
                            self.nowthread += 1
                            Thread(target=self.download_files, args=(url, f"card/cards/{res[:6]}", res)).start()
                        # 能启动新线程则强制跳出无限循环
                        break
                    else:
                        if self.threadLock.acquire(True):  # 2、获取锁状态，一个线程有锁时，别的线程只能在外面等着
                            # logger.info(str(self.nowthread) + " thread in running")
                            # 注意，上面的nowthread的输出值可能为if表达式成功时的值，这是因为线程运行的随机性，因为在判断if时的该值和在print时的该值可能因为线程运行缘故导致不同
                            # 这里的nowthread值仅能提示在print这一瞬间有几个线程还在运行，没有结束
                            # print需要上线程锁，否则可能会和线程函数的print产生冲突导致输出错乱（）即一个print执行到一半，另一个print开始执行，结果是两个print的输出值混在一起
                            self.threadLock.release()  # 3、释放锁
            # except Exception as e:
            #     errorMsg='start new thread to downLoad error:\n'+str(e)
            #     logger.error(errorMsg)

    
    def download_cards_thumb(self, li, server_dict):
        __url = "https://bestdori.com/assets/{}/thumb/chara/"

        for res in li:
            # try:
                while 1:
                    time.sleep(0.05)
                    if 0 <= self.nowthread <= self.maxThread:
                        url = f'{__url.format(server_dict[res.split("_")[1]])}card{str(int(res.split("_")[0])//50).zfill(5)}_rip/{res.split("_")[1]}_{res.split("_", maxsplit = 2)[2]}'
                        if url not in self.get_bad_url():
                            self.nowthread += 1     
                            Thread(target=self.download_files, args=(url, f"card/cards_thumb", res.split("_", maxsplit = 1)[1])).start()
                        break
                    else:
                        if self.threadLock.acquire(True): 
                            # logger.info(str(self.nowthread) + " thread in running")
                            self.threadLock.release()
            # except Exception as e:
            #     errorMsg='start new thread to downLoad error:\n'+str(e)
            #     logger.error(errorMsg)

    def download_degrees(self, li, server):
        __url = f"https://bestdori.com/assets/{server}/thumb/degree_rip/"
        
        for res in li:
            try:
                while 1:
                    time.sleep(0.05)
                    if 0 <= self.nowthread <= self.maxThread:
                        url = f'{__url}{res}'
                        if url not in self.get_bad_url():
                            self.nowthread += 1
                            Thread(target=self.download_files, args=(url, f"degrees/{server}", res)).start()
                        break
                    else:
                        if self.threadLock.acquire(True):
                            # logger.info(str(self.nowthread) + " thread in running")
                            self.threadLock.release()
            except Exception as e:
                errorMsg='DOWNLOAD: '+str(e)
                logger.error(errorMsg)
                
download = Download()


if USE_CACHE:
    logger.info("GLOBAL: 将使用CACHE")
else:
    logger.info("GLOBAL: 将不使用CACHE")


def get_font(name: str, size: int):
    '''
    获取ImageFont.truetype字体

    `name`: `ksm`/`grpcn`/`grpjp`

    `size`: 字体大小
    '''
    path = {
        "ksm": os.path.abspath("data/fonts/KasumiFont.ttf"),
        "grpcn": os.path.abspath("data/fonts/GB18030.ttf"),
        "grpjp": os.path.abspath("data/fonts/TT-Shin Go M.ttf")
    }
    return ImageFont.truetype(path[name], size)

def check_initialized(func):
    '''
    装饰器函数：检查对象是否已初始化
    '''
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        if not self.initialized:
            raise RuntimeError("函数在执行 initialize() 之前不能调用！")
        return await func(self, *args, **kwargs)
    
    return wrapper


class _Card:
    '''
    卡牌信息获取
    '''

    def __init__(self):
        self.initialized = False

    async def initialize(self):
        logger.info("DATA.CARD: 正在初始化")

        await self._get_data()
        await self._load_imgs()
        await self._load_texts()

        self._scheduler = AsyncIOScheduler()
        self._scheduler.add_job(self._get_data, 'interval', hours=1)
        self._scheduler.start()

        logger.success("DATA.CARD: 成功初始化")
        self.initialized = True

    async def _get_data(self):
        if not USE_CACHE:
            summary_url = "https://bestdori.com/api/cards/all.5.json"
            self.__summary_data__: dict = json.loads(requests.get(summary_url).text)
        else:
            with open(os.path.abspath("./cache/all.5.json"), 'r', encoding="UTF-8") as f: self.__summary_data__: dict = json.load(f)
        logger.success("DATA.CARD: 成功获取卡牌简略数据")

        self.__processed_data__ = {k: v for k, v in self.__summary_data__.items() if int(k) < 5001 and v["type"] != "others"}
        for k, v in self.__processed_data__.items():
            self.__processed_data__[k]["bandId"] = (v["characterId"] - 1) // 5 + 1

        path = os.path.abspath("./data/card/data")

        # 先判断有没有卡牌更新
        names = []
        for root, dirs, files in os.walk(path):
            names += (files)

        card_names = {name[:-5] for name in names}

        updated_cards = set(self.__summary_data__.keys()) - card_names

        if updated_cards:
            # 如果有卡牌更新
            logger.info(f"DATA.CARD: 日服卡牌数据更新 {updated_cards}")
            await self._update_card_data(updated_cards)
        
        updated_cards = set()

        # 再检查国服有没有更新
        # 这里使用`prefix`判断
        logger.info("DATA.CARD: 校验数据中")
        for card_id in self.__summary_data__.keys():
            if os.path.exists(f'{path}/{card_id}.json'):
                with open(f'{path}/{card_id}.json', 'r', encoding="UTF-8") as f:
                    card_data: dict = json.load(f)
                    if not card_data["prefix"][CN] and self.__summary_data__[card_id]["prefix"][CN]:
                        updated_cards.add(card_id)
            else:
                updated_cards.add(card_id)
        logger.info("DATA.CARD: 数据校验结束")

        if updated_cards:
            # 如果有国服更新
            logger.info(f"DATA.CARD: 国服卡牌数据更新 {updated_cards}")
            await self._update_card_data(updated_cards)

        # 更新立绘、缩略图
        await self._update_card_img()

    async def _fetch_card_data(self, session, card_id):
        url = f"https://bestdori.com/api/cards/{card_id}.json"
        async with session.get(url) as response:
            return card_id, await response.json()

    async def _update_card_data(self, updated_cards):
        async with aiohttp.ClientSession() as session:
            tasks = [self._fetch_card_data(session, card_id) for card_id in updated_cards]
            card_data_list = await asyncio.gather(*tasks)
            for card_id, card_data in card_data_list:
                logger.success(f"DATA.CARD: 成功获取 {card_id} 的详细数据")
                await asyncio.sleep(0.05)
                with open(os.path.abspath(f"./data/card/data/{card_id}.json"), "w", encoding="UTF-8") as json_file:
                    json.dump(card_data, json_file, ensure_ascii=False, indent=4)

    async def _update_card_img(self):
        res, res_thumb, server_dict = [], [], {}
        
        bad_res, bad_res_thumb = await self._get_bad_res()

        for i,v in self.__summary_data__.items():
            res_data, server = await self._get_res_info(i)
            server_dict[v["resourceSetName"]] = server
            if res_data["normal"]:
                res.append(f'{v["resourceSetName"]}_card_normal.png')
                res_thumb.append(f'{v["resourceSetName"]}_normal.png')
            if res_data["trained"]:
                res.append(f'{v["resourceSetName"]}_card_after_training.png')  
                res_thumb.append(f'{v["resourceSetName"]}_after_training.png')

        _miss_cards = list(set(res).difference(set(await self._get_file_name(os.path.abspath(f'./data/card/cards')))))
        _miss_cards_thumb = list(set(res_thumb).difference(set(os.listdir(os.path.abspath(f'./data/card/cards_thumb')))))

        miss_cards, miss_cards_thumb = [], []

        for v in _miss_cards:
            if v not in bad_res:
                miss_cards.append(v)

        for v in _miss_cards_thumb:
            if v not in bad_res_thumb:
                miss_cards_thumb.append(await self._res2id(v[:9]) + "_" + v)

        if len(miss_cards) > 0 :
            logger.warning(f"DATA.CARD: 卡面资源未下载: {miss_cards}")
            logger.info("DATA.CARD: 开始尝试下载卡面资源")
            download.download_cards(miss_cards, server_dict)
        else:
            logger.info("DATA.CARD: 卡面资源加载成功")

        if len(miss_cards_thumb) > 0 :
            logger.warning(f"DATA.CARD: 缩略图资源未下载: {miss_cards_thumb}")
            logger.info("DATA.CARD: 开始尝试下载缩略图资源")
            download.download_cards_thumb(miss_cards_thumb, server_dict)
        else:
            logger.info("DATA.CARD: 缩略图资源加载成功")

    async def _get_file_name(self, file_dir):
        names = []
        for root, dirs, files in os.walk(file_dir):
            names += files
        return names
    
    async def _get_bad_res(self) -> tuple:
        res_lst = []
        id_lst = []
        for s in download.get_bad_url():
            if 'characters' in s:
                res_id = s.split('/')[7].split('_')[0][3:]
                if 'after_training' in s:
                    res_lst.append(f'res{res_id}_card_after_training.png')
                elif 'normal' in s:
                    res_lst.append(f'res{res_id}_card_normal.png')
            elif 'thumb' in s:
                res_id = s.split('/')[-1].split('_')[0]
                if 'normal' in s:
                    id_lst.append(f'{res_id}_normal.png')
                elif 'after_training' in s:
                    id_lst.append(f'{res_id}_after_training.png')
        return res_lst, id_lst

    async def _get_res_info(self, card_id: int) -> tuple:
        card_id = str(card_id)
        type = self.__summary_data__[card_id]["type"]
        server = "jp"
        for i in [0, 3, 2, 1, 4]:
            if self.__summary_data__[card_id]["prefix"][i]:
                server = ["jp", "en", "tw", "cn", "kr"][i]
                break
        
        result_map = {
            "initial": ({"normal": True, "trained": False}, server),
            "permanent": ({"normal": True, "trained": True if self.__summary_data__[card_id]["stat"].get("training") else False}, server),
            "event": ({"normal": True, "trained": True if self.__summary_data__[card_id]["stat"].get("training") else False}, server),
            "limited": ({"normal": True, "trained": True  if self.__summary_data__[card_id]["stat"].get("training") else False}, server),
            "campaign": ({"normal": True, "trained": True  if self.__summary_data__[card_id]["stat"].get("training") else False}, server),
            "others": ({"normal": True if self.__summary_data__[card_id]["stat"].get("training") else False, "trained": True}, server),
            "dreamfes": ({"normal": True, "trained": True}, server),
            "birthday": ({"normal": False, "trained": True}, server),
            "kirafes": ({"normal": False, "trained": True}, server)
        }

        return result_map[type]

    async def _res2id(self, res: str):
        for k,v in self.__summary_data__.items():
            if v["resourceSetName"] == res:
                return k

    async def _load_imgs(self):
        self.attribute_img = {
            'cool': Image.open(os.path.abspath(f'./data/card/attribute/cool.png')).convert("RGBA"),
            'happy': Image.open(os.path.abspath(f'./data/card/attribute/happy.png')).convert("RGBA"),
            'powerful': Image.open(os.path.abspath(f'./data/card/attribute/powerful.png')).convert("RGBA"),
            'pure': Image.open(os.path.abspath(f'./data/card/attribute/pure.png')).convert("RGBA")
        }
        self.attribute_thumb_img = {
            'cool': self.attribute_img["cool"].resize((45, 45), Image.Resampling.LANCZOS).convert("RGBA"),
            'happy': self.attribute_img["happy"].resize((45, 45), Image.Resampling.LANCZOS).convert("RGBA"),
            'powerful': self.attribute_img["powerful"].resize((45, 45), Image.Resampling.LANCZOS).convert("RGBA"),
            'pure': self.attribute_img["pure"].resize((45, 45), Image.Resampling.LANCZOS).convert("RGBA")
        }
        self.star_img = Image.open(os.path.abspath(f'./data/card/star/star.png')).convert("RGBA")
        self.star_normal_img = Image.open(os.path.abspath(f'./data/card/star/star_normal.png')).convert("RGBA")
        self.star_thumb_img = self.star_img.resize((28, 28), Image.Resampling.LANCZOS)#.convert("RGBA")
        self.star_normal_thumb_img = self.star_normal_img.resize((28, 28), Image.Resampling.LANCZOS)#.convert("RGBA")
        self.frame_img = {
            "1_cool": Image.open(os.path.abspath(f'./data/bg/frame_1_cool.png')).convert("RGBA"),
            "1_happy": Image.open(os.path.abspath(f'./data/bg/frame_1_happy.png')).convert("RGBA"),
            "1_powerful": Image.open(os.path.abspath(f'./data/bg/frame_1_powerful.png')).convert("RGBA"),
            "1_pure": Image.open(os.path.abspath(f'./data/bg/frame_1_pure.png')).convert("RGBA"),
            "2": Image.open(os.path.abspath(f'./data/bg/frame_2.png')).convert("RGBA"),
            "3": Image.open(os.path.abspath(f'./data/bg/frame_3.png')).convert("RGBA"),
            "4": Image.open(os.path.abspath(f'./data/bg/frame_4.png')).convert("RGBA"),
            "5": Image.open(os.path.abspath(f'./data/bg/frame_5.png')).convert("RGBA"),
        }        
        self.frame_large_img = {
            "1_cool": Image.open(os.path.abspath(f'./data/card/res/frame_1_cool.png')).convert("RGBA"),
            "1_happy": Image.open(os.path.abspath(f'./data/card/res/frame_1_happy.png')).convert("RGBA"),
            "1_powerful": Image.open(os.path.abspath(f'./data/card/res/frame_1_powerful.png')).convert("RGBA"),
            "1_pure": Image.open(os.path.abspath(f'./data/card/res/frame_1_pure.png')).convert("RGBA"),
            "2": Image.open(os.path.abspath(f'./data/card/res/frame_2.png')).convert("RGBA"),
            "3": Image.open(os.path.abspath(f'./data/card/res/frame_3.png')).convert("RGBA"),
            "4": Image.open(os.path.abspath(f'./data/card/res/frame_4.png')).convert("RGBA"),
            "5": Image.open(os.path.abspath(f'./data/card/res/frame_5.png')).convert("RGBA"),
        }
        self.band_img = {
            "1": Image.open(os.path.abspath(f'./data/bg/poppinparty.png')).resize((256, 112), Image.Resampling.BILINEAR).convert("RGBA"),
            "2": Image.open(os.path.abspath(f'./data/bg/afterglow.png')).resize((256, 112), Image.Resampling.BILINEAR).convert("RGBA"),
            "3": Image.open(os.path.abspath(f'./data/bg/hellohappyworld.png')).resize((256, 112), Image.Resampling.BILINEAR).convert("RGBA"),
            "4": Image.open(os.path.abspath(f'./data/bg/pastelpalettes.png')).resize((256, 112), Image.Resampling.BILINEAR).convert("RGBA"),
            "5": Image.open(os.path.abspath(f'./data/bg/roselia.png')).resize((256, 112), Image.Resampling.BILINEAR).convert("RGBA"),
            "6": Image.open(os.path.abspath(f'./data/bg/morfonica.png')).resize((256, 112), Image.Resampling.BILINEAR).convert("RGBA"),
            "7": Image.open(os.path.abspath(f'./data/bg/raiseasuilen.png')).resize((256, 112), Image.Resampling.BILINEAR).convert("RGBA")
        }
        self.thumb_bg = Image.open(os.path.abspath(f'./data/bg/thumb_bg.png')).convert("RGBA")
        self.gr_img = Image.open(os.path.abspath(f'./data/bg/gr.png')).convert("RGBA")
        self.level_img = Image.open(os.path.abspath(f'./data/bg/level.png')).convert("RGBA")
        self.watermark = Image.open(os.path.abspath(f'./data/bg/watermark.png')).convert("RGBA")
        logger.success("DATA.CARD: 图片加载成功")

    async def _load_texts(self):
        self.characterId2name = {
            '1': ['戸山 香澄', '戸山香澄', 'kasumi toyama', 'kasumitoyama', '戶山 香澄', '戶山香澄', '户山 香澄', '户山香澄', '香 澄', 'kasumi', '猫', '香澄', '戸山', 'toyama', '戶山', '户山', 'ksm', 'cdd', 'dd', '猫猫头', '猫耳', '香香', '小香', '澄澄', '小香澄', '吉太'],
            '2': ['花園 たえ', '花園たえ', 'tae hanazono', 'taehanazono', '花園 多惠', '花園多惠', '花园 多 惠', '花园多惠', 'たえ', 'tae', '多惠', '花園', 'hanazono', '花園', '花园', 'otae', '惠惠', '多英', '小花', '小惠', '铁 头'],
            '3': ['牛込 りみ', '牛込りみ', 'rimi ushigome', 'rimiushigome', '牛込 里美', '牛込里美', '牛込 里美', '牛込里美', 'りみ', 'rimi', '里美', '里美', '牛込', 'ushigome', '牛込', '牛込', '李美丽', '螺', '丽丽', '阿丽', 'rimili', 'rmr'],
            '4': ['山吹 沙綾', '山吹沙綾', 'saya yamabuki', 'sayayamabuki', '山吹 沙綾', '山吹沙綾', '山吹 沙绫', '山吹沙绫', '沙綾', 'saya', '沙綾', '沙绫', '山吹', 'yamabuki', '山吹', '山吹', 'saaya', '面包娘'],
            '5': ['市ヶ谷 有咲', '市ヶ谷有咲', 'arisa ichigaya', 'arisaichigaya', '市谷 有咲', '市谷有咲', '市谷 有咲', '市谷有咲', '有咲', 'arisa', '有咲', '有咲', '市ヶ谷', 'ichigaya', '市谷', '市谷', 'arisa', 'ars', '贴纸', '豆苗'],
            '6': ['美竹 蘭', '美竹蘭', 'ran mitake', 'ranmitake', ' 美竹 蘭', '美竹蘭', '美竹 兰', '美竹兰', '蘭', 'ran', '蘭', '兰', '美竹', 'mitake', '美竹', '美竹', 'lan', '兰兰', '小兰', '兰酱', '扫把', '临光', '扫把头', '澄闪'],
            '7': ['青葉 モカ', '青葉モカ', 'moca aoba', 'mocaaoba', '青葉 摩卡', '青葉摩卡', '青叶 摩卡', '青叶摩卡', 'モカ', 'moca', '摩卡', '摩卡', '青葉', 'aoba', '青葉', '青叶', '毛力', 'moka', 'mocachan', '摩卡酱', '小摩卡', '卡卡'],
            '8': ['上原 ひまり', '上原ひまり', 'himari uehara', 'himariuehara', '上原 緋瑪麗', '上 原緋瑪麗', '上原 绯玛丽', '上原绯 玛丽', 'ひまり', 'himari', '緋瑪麗', '绯玛丽', '上原', 'uehara', '上原', '上原', '肥玛丽', 'hmr', 'aao'],
            '9': ['宇田川 巴', '宇田川巴', 'tomoe udagawa', 'tomoeudagawa', '宇田川 巴', '宇田川巴', '宇田川 巴', '宇田川巴', '巴', 'tomoe', '巴', '巴', 'mio', 'tme', '巴姐', '巴哥', 'soiya', '凯尔希'],
            '10': ['羽沢 つぐみ', '羽沢つぐみ', 'tsugumi hazawa', 'tsugumihazawa', '羽澤 鶇', '羽澤鶇', '羽泽 鸫', '羽泽鸫', 'つぐみ', 'tsugumi', '鶇', '鸫', '羽沢', 'hazawa', '羽澤', '羽泽', '茨菇', '茨菇', '刺骨', 'tsugu', 'tsg', '白面鸮', '鸫鸫', ' 菇'],
            '11': ['弦巻 こころ', '弦巻こころ', 'kokoro tsurumaki', 'kokorotsurumaki', '弦卷 心', '弦卷心', '弦卷 心', '弦卷心', 'こころ', 'kokoro', '心', '心', '弦巻', 'tsurumaki', '弦卷', '弦卷', 'kkr', '心心', '心仔', '小心心', '富婆心'],
            '12': ['瀬田 薫', '瀬田薫', 'kaoru seta', 'kaoruseta', '瀨田 薰', '瀨田薰', '濑田 薰', '濑田薰', '薫', 'kaoru', '薰', ' 薰', '瀬田', 'seta', '瀨田', '濑 田', '儚い', '梦幻', '夢幻', '薰哥哥', '薰哥', '薰酱', '哈卡奶', 'hakanai', '烤炉'],
            '13': ['北沢 はぐみ', '北沢はぐみ', 'hagumi kitazawa', 'hagumikitazawa', '北澤 育美', '北澤育美', '北泽 育美', '北泽育美', 'はぐみ', 'hagumi', '育美', '育 美', '北沢', 'kitazawa', '北澤', '北泽', 'hgm', '育育'],
            '14': ['松原 花音', '松原花音', 'kanon matsubara', 'kanonmatsubara', '松原 花音', '松原花音', '松原 花音', '松原花音', '花音', 'kanon', '花音', '花音', '松原', 'matsubara', '松原', ' 松原', '水母', '卡农', '小花音'],
            '15': ['奥沢 美咲', '奥沢美咲', 'misaki okusawa', 'misakiokusawa', '奧澤 美咲', '奧澤 美咲', '奥泽 美咲', '奥泽美咲', '美咲', 'misaki', '美咲', '美咲', '奥沢', 'okusawa', '奧澤', '奥泽', '米歇尔', '米歇爾', '熊', '熊', 'michele', 'msk', '米 谢噜', '阿米娅'],
            '16': ['丸山 彩', '丸山彩', 'aya maruyama', 'ayamaruyama', '丸山 彩', '丸山彩', '丸山 彩', '丸山彩', '彩', 'aya', '彩', '彩彩', '丸山', 'maruyama', '丸山', '丸山', '小彩', '彩酱', '彩姐', '阿彩'],
            '17': ['氷川 日菜', '氷川日菜', 'hina hikawa', 'hinahikawa', '冰川 日菜', '冰川日菜', '冰川 日菜', '冰川日菜', '日菜', 'hina', '噜', 'run', '邪神', '吉他'],
            '18': ['白鷺 千聖', '白鷺千聖', 'chisato shirasagi', 'chisatoshirasagi', '白鷺 千聖', '白鷺千聖', '白鹭 千圣', '白鹭千圣', '千聖', 'chisato', '千聖', '千圣', '白鷺', 'shirasagi', '白鷺', '白鹭', 'cst', '小千', '千酱', '小千圣'],
            '19': ['大和 麻弥', '大和麻弥', 'maya yamato', 'mayayamato', '大和 麻彌', '大 和麻彌', '大和 麻弥', '大和麻弥', '麻弥', 'maya', '麻彌', '麻弥', '大和', 'yamato', '大和', '大和', '大和妈咪', '妈咪', '妈呀', '玛雅'],
            '20': ['若宮 イヴ', '若宮イヴ', 'eve wakamiya', 'evewakamiya', '若宮 伊芙', '若宮伊芙', '若宫 伊芙', ' 若宫伊芙', 'イヴ', 'eve', '伊芙', '伊芙', '若宮', 'wakamiya', '若宮', '若宫', 'if', '武士道', '阿芙', '阿福', '伊芙酱', '小伊芙', '小芙', 'bushido'],
            '21': ['湊 友希那', '湊友希那', 'yukina minato', 'yukinaminato', '湊 友希那', '湊友希那', '凑 友希那', '凑友希那', '友希那', 'yukina', '友希那', '友希那', '湊', 'minato', '湊', '凑', '有希那', 'ykn', '企鹅', ' 憋笑', 'i83', '凑女人', '猫奴'],
            '22': ['氷川 紗夜', '氷川紗夜', 'sayo hikawa', 'sayohikawa', '冰川 紗夜', '冰川紗夜', '冰川 纱夜', '冰川纱夜', '紗夜', 'sayo', '紗夜', '纱夜', 'hikawa'],
            '23': ['今井 リサ', '今井リサ', 'lisa imai', 'lisaimai', '今井 莉莎', '今井莉莎', '今井 莉莎', '今井莉莎', 'リサ', 'lisa', '莉莎', '莉莎', '今井', 'imai', '今井', '今 井', 'risa', 'Lisa姐', 'Lisa内', '锂砂镍'],
            '24': ['宇田川 あこ', '宇田川あこ', 'ako udagawa', 'akoudagawa', '宇田川 亞 子', '宇田川亞子', '宇田川 亚子', '宇田川亚子', 'あこ', 'ako', '亞子', '亚子', 'udagawa', '阿仔', '小亚子'],
            '25': ['白金 燐子', '白金燐子', 'rinko shirokane', 'rinkoshirokane', '白金 燐子', '白金燐子', '白金 燐子', '白金燐子', '燐子', 'rinko', '燐子', '燐子', '白金', 'shirokane', '白金', '白金', 'rinrin', '燐', '燐', '燐燐', '燐仔', '燐姐', '小燐', '燐可', '……', '提词姬', '燐燐'],
            '26': ['倉田 ましろ', '倉田ましろ', 'mashiro kurata', 'mashirokurata', '倉田 真白', '倉田真白', 'ましろ', 'mashiro', '真白', '倉田', 'kurata', '倉田', '仓田真白', '仓田 真白', 'msr', '小白', '小哥', '仓神', ' 小我7邀'],
            '27': ['桐ヶ谷 透子', '桐ヶ谷透子', 'toko kirigaya', 'tokokirigaya', '桐谷 透子', '桐谷透子', '透子', 'toko', '透子', ' 桐ヶ谷', 'kirigaya', '桐谷'],
            '28': ['広町 七深', '広町七深', 'nanami hiromachi', 'nanamihiromachi', '廣町 七深', '廣町七深', '七深', 'nanami', '七深', '広町', 'hiromachi', '廣町', 'nnm', 'nil'],
            '29': ['二葉 つくし', '二葉つくし', 'tsukushi futaba', 'tsukushifutaba', '二葉 筑紫', '二葉筑紫', 'つくし', 'tsukushi', '筑紫', '二葉', 'futaba', '二葉', '土笔', '土筆', 'tks', '二叶筑紫', '二叶', '筑笔'],
            '30': ['八潮 瑠唯', '八潮瑠唯', 'rui yashio', 'ruiyashio', '八潮 瑠唯', '八潮瑠唯', '瑠唯', 'rui', '瑠唯', '八潮', 'yashio', '八潮', 'yso'],
            '31': ['和奏 レイ', '和奏レイ', 'rei wakana', 'reiwakana', '和奏 瑞依', '和奏瑞依', 'レイ', 'rei', '瑞依', '和奏', 'wakana', '和奏', 'レイヤ', 'layer', '大姐头'],
            '32': ['朝日 六花', '朝日六花', 'rokka asahi', 'rokkaasahi', '朝日 六花', '朝日六花', '六花', 'rokka', '六花', '朝日', 'asahi', '朝日', 'ロック', 'lock', '六六', 'LOCK', 'bz的主人', '桑葚'],
            '33': ['佐藤 ますき', '佐藤ますき', 'masuki sato', 'masukisato', '佐藤 益木', '佐藤益木', 'ますき', 'masuki', '益木', ' 佐藤', 'sato', '佐藤', 'マスキング', 'masking', 'masking', '狂犬', '狂犬', 'king'],
            '34': ['鳰原 令王那', '鳰原令王那', 'reona nyubara', 'reonanyubara', '鳰原 令王那', '鳰 原令王那', '令王那', 'reona', '令王那', '鳰原', 'nyubara', '鳰原', 'パレオ', 'pareo', 'pareo', '忠犬PARE公', '暗黑丸山彩', 'reo'],
            '35': ['珠手 ちゆ', '珠手ちゆ', 'chiyu tamade', 'chiyutamade', '珠手 知由', '珠手知由', 'ちゆ', 'chiyu', '知 由', '珠手', 'tamade', '珠手', 'チュチュ', 'chu2', 'chu²', 'chuchu', 'chu平方', '猫耳', '猫耳', '楚萍芳', '牙白']
        }
        self.band2name = {
            "1": ["Popipa", "ppp", "Poppin Party", "破琵琶"],
            "2": ["Afterglow", "ag"],
            "3": ["Hello Happy World", "hhw", "hellohappy"],
            "4": ["paspale", "pp"],
            "5": ["Roselia", "r", "R"],
            "6": ["Monica", "Morfonica", "monica", "m", "蝶"],
            "7": ["Raise A Suilen", "RAS", "ras"],
        }
        self.chinese2attribute = {
            'cool': ["蓝", "cool"],
            'happy': ["黄", "橙", "happy", "乐"],
            'powerful': ["红", "powerful"],
            'pure': ["绿", "纯", "pure"]
        }
        self.chinese2rarity = {
            "1": ["1", "1星", "一", "一星"],
            "2": ["2", "2星", "二", "二星"],
            "3": ["3", "3星", "三", "三星"],
            "4": ["4", "4星", "四", "四星"],
            "5": ["5", "5星", "五", "五星"]
        }
        self.chinese2type = {
            'initial': ["初始", "初始卡面"],
            'permanent': ["常驻", "常驻卡面", "无期限"], 
            'event': ["活动", "活动卡面"], 
            'limited': ["期间限定", "限定", "限定卡面", "期间限定卡面"], 
            'campaign': ["联名合作", "联动", "联名合作卡面", "联动卡面"], 
            'others': ["其它", "其他", "其他卡面"], 
            'dreamfes': ["dfes", "梦限", "dreamfes", "fes"], 
            'birthday': ["生日", "birth", "生日卡", "birthday"], 
            'kirafes': ["kfes", "kirafes", "闪限", "fes"],
        }

        self.band_list = [x for v in self.band2name.values() for x in v]
        self.attribute_list = [x for v in self.chinese2attribute.values() for x in v]
        self.rarity_list = [x for v in self.chinese2rarity.values() for x in v]
        self.type_list = [x for v in self.chinese2type.values() for x in v]
        logger.success("DATA.CARD: 文本数据加载成功")


    # 文字数据获取

    @check_initialized
    async def get_data(self, card_id: int) -> dict:
        '''
        获取卡牌对应的详细信息
        '''
        with open(os.path.abspath(f"./data/card/data/{card_id}.json"), 'r', encoding="UTF-8") as f: 
            data: dict = json.load(f)
        return data

    @check_initialized
    async def get_character_id(self, card_id: int) -> int:
        '''
        获取卡牌对应的角色ID
        '''
        return (await self.get_data(card_id))["characterId"]
    
    @check_initialized
    async def get_band_id(self, card_id: int) -> int:
        '''
        获取卡牌对应的乐团ID
        '''
        return (await self.get_character_id(card_id) - 1) // 5 + 1
    
    @check_initialized
    async def get_rarity(self, card_id: int) -> int:
        '''
        获取卡牌对应的稀有度
        '''
        return (await self.get_data(card_id))["rarity"]

    @check_initialized
    async def get_attribute(self, card_id: int) -> str:
        '''
        获取卡牌对应的属性
        '''
        return (await self.get_data(card_id))["attribute"]

    @check_initialized
    async def get_type(self, card_id: int) -> str:
        '''
        获取卡牌对应的类型
        '''
        return (await self.get_data(card_id))["type"]

    @check_initialized
    async def get_level_limit(self, card_id: int) -> int:
        '''
        获取卡牌对应的等级上限
        '''
        return (await self.get_data(card_id))["levelLimit"]

    @check_initialized
    async def get_resource_set_name(self, card_id: int) -> str:
        '''
        获取卡牌对应的资源集名称
        '''
        return (await self.get_data(card_id))["resourceSetName"]

    @check_initialized
    async def get_sd_resource_name(self, card_id: int) -> str:
        '''
        获取卡牌对应的SD资源名称
        '''
        return (await self.get_data(card_id))["sdResourceName"]

    @check_initialized
    async def get_episodes(self, card_id: int) -> list:
        '''
        获取卡牌对应的故事列表
        '''
        if card_id > 5000:
            raise ValueError(f"{card_id} 没有对应的故事列表")
        return (await self.get_data(card_id))["episodes"]["entries"]

    @check_initialized
    async def get_episode_title(self, card_id: int) -> Tuple[list]:
        '''
        获取卡牌故事的标题列表
        '''
        episodes = await self.get_episodes(card_id)
        return episodes[0]["title"], episodes[1]["title"]

    @check_initialized
    async def get_costume_id(self, card_id: int) -> int:
        '''
        获取卡牌对应的服装ID
        '''
        return (await self.get_data(card_id))["costumeId"]

    @check_initialized
    async def get_gacha_text(self, card_id: int) -> list:
        '''
        获取卡牌对应的招募文本
        '''
        return (await self.get_data(card_id))["gachaText"]

    @check_initialized
    async def get_prefix(self, card_id: int) -> list:
        '''
        获取卡牌对应的名称
        '''
        return (await self.get_data(card_id))["prefix"]

    @check_initialized
    async def get_released_at(self, card_id: int) -> list:
        '''
        获取卡牌对应的发布日期
        '''
        return (await self.get_data(card_id))["releasedAt"]

    @check_initialized
    async def get_skill_name(self, card_id: int) -> list:
        '''
        获取卡牌对应的技能名称
        '''
        return (await self.get_data(card_id))["skillName"]

    @check_initialized
    async def get_skill_id(self, card_id: int) -> int:
        '''
        获取卡牌对应的技能ID
        '''
        return (await self.get_data(card_id))["skillId"]

    @check_initialized
    async def get_source(self, card_id: int) -> list:
        '''
        获取卡牌对应的来源
        '''
        return (await self.get_data(card_id))["source"]
    
    @check_initialized
    async def get_trained_level(self, card_id: int) -> str:
        '''
        获取卡牌特训后的等级
        '''
        level_limit = await self.get_level_limit(card_id)
        level_limit_train = (await self.get_data(card_id)).get("stat", {}).get("training", {}).get("levelLimit", 0)
        return str(level_limit + level_limit_train)

    @check_initialized
    async def get_stat(self, card_id: int) -> dict:
        '''
        获取卡牌对应的综合力
        '''
        return (await self.get_data(card_id))["stat"]
    
    @check_initialized
    async def get_level_stat(self, card_id: int, level: str, trained: bool) -> dict:
        '''
        获取卡牌对应等级的综合力
        '''
        stats = await self.get_stat(card_id)
        if level not in stats:
            raise ValueError(f"{card_id} 不存在 {level} 等级")

        level_stat = stats[level]
        total_stat = sum(level_stat.values())

        if stats.get("episodes"):
            episodes_stat = stats["episodes"]
            level_stat["performance"] += episodes_stat[0]["performance"] + episodes_stat[1]["performance"]
            level_stat["technique"] += episodes_stat[0]["technique"] + episodes_stat[1]["technique"]
            level_stat["visual"] += episodes_stat[0]["visual"] + episodes_stat[1]["visual"]
            total_stat += sum(stats["episodes"][0].values()) + sum(stats["episodes"][1].values())

        if trained:
            training_stat = stats["training"]
            level_stat["performance"] += training_stat["performance"]
            level_stat["technique"] += training_stat["technique"]
            level_stat["visual"] += training_stat["visual"]
            training_stat["levelLimit"] = 0
            training_total = sum(training_stat.values())
            total_stat += training_total

        level_stat["total"] = total_stat
        return level_stat
    
    @check_initialized
    async def get_max_stat(self, card_id: int) -> dict:
        '''
        获取卡牌的最大综合力
        '''
        return await self.get_level_stat(card_id, await self.get_trained_level(card_id), (await self._get_res_info(card_id))[0]["trained"])

    @check_initialized
    async def get_character_ids(self, character_name: str):
        return [character for character in self.characterId2name.keys() if character_name in self.characterId2name[character]]
    
    @check_initialized
    async def get_band_ids(self, band_name: str):
        return [band for band in self.band2name.keys() if band_name in self.band2name[band]]

    @check_initialized
    async def get_attribute_types(self, attribute_ch: str):
        return [attribute for attribute in self.chinese2attribute.keys() if attribute_ch in self.chinese2attribute[attribute]]

    @check_initialized
    async def get_rarities(self, rarity_ch: str):
        return [rarity for rarity in self.chinese2rarity.keys() if rarity_ch in self.chinese2rarity[rarity]]
            
    @check_initialized
    async def get_types(self, type_ch: str):
        return [type for type in self.chinese2type.keys() if type_ch in self.chinese2type[type]]

    @check_initialized
    async def get_card_id(self, mode: str, keywords: list) -> list:
        '''
        获取指定的卡面id
        `mode`: 可选`["attribute", "characterId", "bandId", "rarity", "type"]`
        `keywords`: 请参照Bestdori API
        '''
        if mode not in ["attribute", "characterId", "rarity", "bandId", "type"]:
            raise ValueError("Undefined parameters.")
        
        card_ids = []
        for key, value in self.__processed_data__.items():
            if str(value[mode]) in keywords:
                card_ids.append(int(key))
        return card_ids

    # 图片数据获取

    @check_initialized
    async def get_res(self, card_id: int) -> dict:
        '''
        获取卡牌对应的立绘
        
        return:
        ```
        {
            "normal": PIL.Image.Image,
            "trained": PIL.Image.Image
        }
        ```
        '''
        resourceSetName = await self.get_resource_set_name(card_id)
        normal_path = os.path.abspath(f'./data/card/cards/{resourceSetName[:6]}/{resourceSetName}_card_normal.png')
        training_path = os.path.abspath(f'./data/card/cards/{resourceSetName[:6]}/{resourceSetName}_card_after_training.png')

        res_info, server = await self._get_res_info(card_id)
        normal, trained = res_info["normal"], res_info["trained"]
        result = {}
        if normal:
            result["normal"] = Image.open(normal_path).convert("RGBA")
        if trained:
            result["trained"] = Image.open(training_path).convert("RGBA")

        return result
    
    @check_initialized
    async def get_thumb_res(self, card_id: int) -> dict:
        '''
        获取卡牌对应的缩略图
        
        return:
        ```
        {
            "normal": PIL.Image.Image,
            "trained": PIL.Image.Image
        }
        ```
        '''
        resourceSetName = await self.get_resource_set_name(card_id)
        normal_path = os.path.abspath(f'./data/card/cards_thumb/{resourceSetName}_normal.png')
        training_path = os.path.abspath(f'./data/card/cards_thumb/{resourceSetName}_after_training.png')

        res_info, server = await self._get_res_info(card_id)
        normal, trained = res_info["normal"], res_info["trained"]
        result = {}
        try:
            if normal:
                result["normal"] = Image.open(normal_path).convert("RGBA")
        except FileNotFoundError:
            pass
        try:
            if trained:
                result["trained"] = Image.open(training_path).convert("RGBA")
        except FileNotFoundError:
            pass

        return result
    
    @check_initialized
    async def get_band_icon(self, card_id: int) -> Image.Image:
        '''
        获取卡牌对应的乐队图标
        '''
        band_id = await self.get_band_id(card_id)
        return Image.open(os.path.abspath(f'./data/card/res/band_{band_id}.png')).convert("RGBA")
    

class _Skill:
    '''
    技能信息获取
    '''
    def __init__(self):
        self.initialized = False

    async def initialize(self):
        logger.info("DATA.SKILL: 正在初始化")

        await self._get_data()

        self._scheduler = AsyncIOScheduler()
        self._scheduler.add_job(self._get_data, 'interval', hours=1)
        self._scheduler.start()

        logger.success("DATA.SKILL: 成功初始化")
        self.initialized = True

    async def _get_data(self):
        if not USE_CACHE:
            url = "https://bestdori.com/api/skills/all.10.json"
            self.__data__: dict = json.loads(requests.get(url).text)
        else:
            with open(os.path.abspath("./cache/all.10.json"), 'r', encoding="UTF-8") as f: self.__data__: dict = json.load(f)
        logger.success("DATA.SKILL: 成功获取技能数据")
    
    @check_initialized
    async def get_skill_data(self, skill_id: str) -> dict:
        '''
        获取技能数据
        '''
        return self.__data__[skill_id]
    
    @check_initialized
    async def get_skill_description(self, skill_id :str) -> str:
        '''
        获取技能描述
        '''
        skill_data = await self.get_skill_data(skill_id)
        description: str = skill_data["description"][CN] if skill_data["description"][CN] else skill_data["description"][JP]
        duration: str = "/".join([str(i) for i in skill_data["duration"]])
        if skill_data.get("onceEffect"):
            onceEffectValue: str = str(skill_data["onceEffect"]["onceEffectValue"][CN]) if skill_data["onceEffect"]["onceEffectValue"][CN] else str(skill_data["onceEffect"]["onceEffectValue"][JP])
            return description.format(onceEffectValue, duration)
        else:
            return description.format(duration)


class _AreaItem:
    '''
    加成信息获取
    '''
    def __init__(self):
        self.initialized = False

    async def initialize(self):
        logger.info("DATA.AREAITEM: 正在初始化")

        await self._get_data()

        self._scheduler = AsyncIOScheduler()
        self._scheduler.add_job(self._get_data, 'interval', hours=1)
        self._scheduler.start()

        logger.success("DATA.AREAITEM: 成功初始化")
        self.initialized = True

    async def _get_data(self):
        if not USE_CACHE:
            url = "https://bestdori.com/api/areaItems/main.5.json"
            self.__data__: dict = json.loads(requests.get(url).text)
        else:
            with open(os.path.abspath("./cache/main.5.json"), 'r', encoding="UTF-8") as f: self.__data__: dict = json.load(f)
        
        for k, data in self.__data__.items():
            for idx, band_id in enumerate(data["targetBandIds"]):
                if 18 == band_id:
                    self.__data__[k]["targetBandIds"][idx] = 7
                if 21 == band_id:
                    self.__data__[k]["targetBandIds"][idx] = 6
        
        logger.success("DATA.AREAITEM: 成功获取加成数据")

    @check_initialized
    async def get_data(self, area_item_category: str) -> dict:
        return self.__data__[area_item_category]
    
    @check_initialized
    async def get_performance_data(self, area_item_category: str, level: str) -> int:
        return (await self.get_data(area_item_category))["performance"][level][0]

    @check_initialized
    async def get_technique_data(self, area_item_category: str, level: str) -> int:
        return (await self.get_data(area_item_category))["technique"][level][0]
    
    @check_initialized
    async def get_visual_data(self, area_item_category: str, level: str) -> int:
        return (await self.get_data(area_item_category))["visual"][level][0]
    
    @check_initialized
    async def get_addition_data(self, area_item_category: str, level: str) -> dict:
        return {
            "performance": (await self.get_performance_data(area_item_category, level)) / 100,
            "technique": (await self.get_technique_data(area_item_category, level)) / 100,
            "visual": (await self.get_visual_data(area_item_category, level)) / 100
        }

    @check_initialized
    async def get_target_attributes(self, area_item_category: str) -> list:
        return (await self.get_data(area_item_category))["targetAttributes"]
    
    @check_initialized
    async def get_target_band_ids(self, area_item_category: str) -> list:
        return (await self.get_data(area_item_category))["targetBandIds"]


class Data(object):
    '''
    数据获取类
    '''
    def __init__(self):
        self.initialized = False
    
    async def initialize(self):
        self.card = _Card()
        self.skill = _Skill()
        self.areaitem = _AreaItem()
        await self.card.initialize()
        await self.skill.initialize()
        await self.areaitem.initialize()

    async def _get_areaitem_matched_card_num(self, card_ids: list, areaitem_dict: dict):
        result = {(await self.card.get_attribute(card_id), await self.card.get_band_id(card_id)): {"performance": 0, "technique": 0, "visual": 0} for card_id in card_ids}
        situation = set()
        for areaitem_id, areaitem_level in areaitem_dict.items():
            attributes_condition = await self.areaitem.get_target_attributes(areaitem_id)
            band_ids_condition = await self.areaitem.get_target_band_ids(areaitem_id)
            for card_id in card_ids:
                attribute = await self.card.get_attribute(card_id)
                band_id = await self.card.get_band_id(card_id)
                situation.add((attribute, band_id))

        for attribute, band_id in situation:
            for areaitem_id, areaitem_level in areaitem_dict.items():
                attributes_condition = await self.areaitem.get_target_attributes(areaitem_id)
                band_ids_condition = await self.areaitem.get_target_band_ids(areaitem_id)
                if attribute in attributes_condition and band_id in band_ids_condition:
                    addition_data = await self.areaitem.get_addition_data(areaitem_id, areaitem_level)
                    result[(attribute, band_id)]["performance"] += addition_data["performance"]
                    result[(attribute, band_id)]["technique"] += addition_data["technique"]
                    result[(attribute, band_id)]["visual"] += addition_data["visual"]
        return result

    async def calculate_final_stat(self, card_stats: dict, areaitem_dict: dict) -> dict:
        '''
        计算乐队总综合力

        param:
        ```
        card_stats = {
            card_id: {
                "performance": ...
            }
        }

        areaitem_dict = {
            areaitem_id: areaitem_level
        }
        ```
        '''
        situations = set()
        stats = {(await self.card.get_attribute(card_id), await self.card.get_band_id(card_id)): {"performance": 0, "technique": 0, "visual": 0} for card_id in card_stats.keys()}
        
        for card_id in card_stats.keys():
            attribute = await self.card.get_attribute(card_id)
            band_id = await self.card.get_band_id(card_id)
            situations.add((attribute, band_id))

        for card_id, card_stat in card_stats.items():
            for attribute, band_id in situations:
                _attribute = await self.card.get_attribute(card_id)
                _band_id = await self.card.get_band_id(card_id)
                if _attribute == attribute and _band_id == band_id:
                    stats[(attribute, band_id)]["performance"] += card_stat["performance"]
                    stats[(attribute, band_id)]["technique"] += card_stat["technique"]
                    stats[(attribute, band_id)]["visual"] += card_stat["visual"]
            
        addition_data = await self._get_areaitem_matched_card_num(card_stats.keys(), areaitem_dict)
        stat_additions = {(await self.card.get_attribute(card_id), await self.card.get_band_id(card_id)): {"performance": 0, "technique": 0, "visual": 0} for card_id in card_stats.keys()}
        for situation, stat in stats.items():
            for stat_type in stat.keys():
                stat_additions[situation][stat_type] = stat[stat_type] * addition_data[situation][stat_type]

        for situation, stat in stats.items():
            for stat_type in stat.keys():
                stats[situation][stat_type] += stat_additions[situation][stat_type]
            stats[situation]["total"] = sum([stat for stat_type, stat in stats[situation].items() if stat_type != "total"])
        stats["total"] = sum([stat["total"] for stat in stats.values()])
        return stats

data = Data()


class Card(object):
    def __init__(self):
        pass

    async def timestamp_to_datetime(self, timestamp: int) -> str:
        if timestamp:
            timestamp = int(timestamp) / 1000  # 转换为秒级时间戳
            dt = datetime.datetime.fromtimestamp(timestamp)
            chinese_datetime = dt.strftime("%Y年%#m月%#d日, %I:%M %p")
            return chinese_datetime
    
    async def extra_get_thumb_card(self, id: int, illust: str, trainingStatus: str):
        im: Image.Image = (await data.card.get_thumb_res(id))["trained" if illust == "after_training" else "normal"]

        rarity = await data.card.get_rarity(id)
        attribute = await data.card.get_attribute(id)
        frame = str(rarity) if rarity != 1 else f"{rarity}_{attribute}"
        band_icon = (await data.card.get_band_icon(id)).resize((48, 48), Image.Resampling.BILINEAR)
        
        im.paste(data.card.frame_img[frame], box=(0, 0), mask=data.card.frame_img[frame].split()[3])
        if trainingStatus == "done":
            for i in range(0, rarity):
                im.paste(data.card.star_thumb_img, box=(4, 180 - (i+1) * 24 - 8), mask=data.card.star_thumb_img.split()[3])
        else:
            for i in range(0, rarity):
                im.paste(data.card.star_normal_thumb_img, box=(4, 180 - (i+1)* 24 - 8), mask=data.card.star_normal_thumb_img.split()[3])
        im.paste(data.card.attribute_thumb_img[attribute], box=(133, 3), mask=data.card.attribute_thumb_img[attribute].split()[3])
        im = ImageUtils.paste(im, band_icon, (2, 2))
        return im
        
    async def make_thumb_card(self, card_id: int, thumb_card: Image.Image, trained: bool) -> Image:
        '''
        生成卡面头像
        `card_id`: 卡面id
        `thumb_card`: 缩略图
        `trained`: 是否训练
        '''        
        rarity = await data.card.get_rarity(card_id)
        attribute = await data.card.get_attribute(card_id)
        frame = str(rarity) if rarity != 1 else f"{rarity}_{attribute}"
        band_icon = (await data.card.get_band_icon(card_id)).resize((48, 48), Image.Resampling.BILINEAR)
        
        thumb_card.paste(data.card.frame_img[frame], box=(0, 0), mask=data.card.frame_img[frame].split()[3])
        if trained:
            for i in range(0, rarity):
                thumb_card.paste(data.card.star_thumb_img, box=(4, 180 - (i+1)* 24 - 8), mask=data.card.star_thumb_img.split()[3])
        else:
            for i in range(0, rarity):
                thumb_card.paste(data.card.star_normal_thumb_img, box=(4, 180 - (i+1)* 24 - 8), mask=data.card.star_normal_thumb_img.split()[3])
        thumb_card.paste(data.card.attribute_thumb_img[attribute], box=(133, 3), mask=data.card.attribute_thumb_img[attribute].split()[3])
        thumb_card = ImageUtils.paste(thumb_card, band_icon, (2, 2))

        return thumb_card

    async def init_thumb(self, card_id: int) -> Image:
        '''
        生成卡面双图
        `card_id`: 卡面id
        '''
        font = get_font("ksm", 28)

        def to_width(string: str) -> int:
            return math.ceil(font.getlength(string))
        
        prefixes = await data.card.get_prefix(card_id)
        prefix = prefixes[CN] or prefixes[JP]

        thumbs = await data.card.get_thumb_res(card_id)
        thumbnails = []
        for k, v in thumbs.items():
            thumbnails.append(await self.make_thumb_card(card_id, v, k=="trained"))
            
        img = Image.new("RGBA", (data.card.thumb_bg.getbbox()[2], data.card.thumb_bg.getbbox()[3]))
        img.paste(data.card.thumb_bg, (0,0), data.card.thumb_bg.split()[3])

        if len(thumbnails) == 1:
            img.paste(thumbnails[0], ((img.getbbox()[2] - thumbnails[0].getbbox()[2])//2, (data.card.thumb_bg.getbbox()[2] - 2*thumbnails[0].getbbox()[2])//3), mask = thumbnails[0].split()[3])
        else:
            img.paste(thumbnails[1], ((data.card.thumb_bg.getbbox()[2] - 2*thumbnails[0].getbbox()[2])//3, (data.card.thumb_bg.getbbox()[2] - 2*thumbnails[0].getbbox()[2])//3), mask = thumbnails[1].split()[3])
            img.paste(thumbnails[0], ((data.card.thumb_bg.getbbox()[2] - 2*thumbnails[0].getbbox()[2])//3 * 2 + thumbnails[0].getbbox()[2], (data.card.thumb_bg.getbbox()[2] - 2*thumbnails[0].getbbox()[2])//3), mask = thumbnails[0].split()[3])

        draw = ImageDraw.Draw(img)
        x, y = (img.getbbox()[2] - to_width(prefix))//2, data.card.thumb_bg.getbbox()[3] - (data.card.thumb_bg.getbbox()[3] - (data.card.thumb_bg.getbbox()[2] - 2*thumbnails[0].getbbox()[2])//3 - thumbnails[0].getbbox()[3])//2 - 28
        draw.text((x, y - 14), prefix, font=font, fill=(0,0,0))
        
        draw.text(((img.getbbox()[2] - to_width(f'{card_id} | {await data.card.get_type(card_id)}'))//2, y + 22), f'{card_id} | {await data.card.get_type(card_id)}', font=font, fill=(0,0,0))
        
        return img

    async def make_thumb_cards_table(self, thumb_cards: list):
        '''
        生成卡面头像预览列表
        `thumb_cards`: 列表嵌套列表装`Image`
        '''
        max_lenth = 0
        for i in thumb_cards:
            if len(i) > max_lenth:
                max_lenth = len(i)

        bg_p = Image.open(os.path.abspath("data/bg/bg_pattern.png"))

        W, H  = data.card.thumb_bg.getbbox()[2], data.card.thumb_bg.getbbox()[3]

        # 生成背景
        width = 36*2 + len(thumb_cards) * W + (len(thumb_cards) - 1) * 48
        height = 36*2 + max_lenth * H + (max_lenth - 1) * 32
        (width_p, height_p) = bg_p.size     #用来拼合的图片的长宽
        width_num = math.ceil(width/width_p)    #拼合的行数和列数（向上取整）
        height_num = math.ceil(height/height_p)
        result_width = width_p * width_num
        result_height = height_p * height_num
        bg = Image.new('RGBA', (result_width, result_height))
        for i in range(width_num):
            for j in range(height_num):
                bg.paste(bg_p, (i*width_p, j*height_p))     #先拼出来一张比要生成的图片的长宽都稍微大一点的背景

        im = bg.crop((0, 0, width, height))

        for idx_i,i in enumerate(thumb_cards):
            for idx_j,j in enumerate(i):
                im.paste(j, box=(36 + idx_i * W + (idx_i) * 48, 36 + idx_j * H + (idx_j) * 32), mask = j.split()[3])
        return im
    
    async def get_cards(self, characterId: int = None, bandId: int = None, attribute: str = None, rarity: int = None, type: str = None):
        '''
        获取符合要求的角色卡面
        `characterId`: 角色ID
        `bandId`: 乐队ID
        `attribute`: 属性
        `rarity`: 稀有度
        `type`: 类型
        '''
        _data, cards = {}, {}

        if characterId:
            _data["characterId"] = characterId
        if bandId:
            _data["bandId"] = bandId

        if attribute:
            _data["attribute"] = attribute
        if rarity:
            _data["rarity"] = rarity
        if type:
            _data["type"] = type

        for key, value in _data.items():
            cards[key] = set(await data.card.get_card_id(key, value))

        merged_cards = []
        if len(cards) == 1:
            merged_cards = list(set.union(*cards.values()))
        else:
            merged_cards = list(set.intersection(*cards.values()))

        if len(merged_cards) == 1:
            return await self.get_card(merged_cards[0])
        elif len(merged_cards) == 0:
            return

        sorted_cards = await self.sort_cards(merged_cards)
        return await self.make_thumb_cards_table(sorted_cards)

    async def make_title(self, _data: dict) -> Image.Image:
        band_id: str = str((_data["characterId"] - 1) // 5 + 1)
        prefix: str = _data["prefix"][CN] or _data["prefix"][JP] or _data["prefix"][TW] or _data["prefix"][EN] or _data["prefix"][KR]
        prefix_width = math.ceil(get_font("grpcn", 36).getlength(prefix))
        character_name: str = data.card.characterId2name[str(_data['characterId'])][0]
        character_name_width = math.ceil(get_font("grpcn", 45).getlength(character_name))
        result: Image.Image = Image.open(os.path.abspath('./data/card/res/title.png')).convert("RGBA")
        result.paste(data.card.band_img[band_id], (72, 32), data.card.band_img[band_id].split()[3])
        draw = ImageDraw.Draw(result)
        draw.text(((result.width - prefix_width)//2, 21), prefix, (84,84,84), get_font("grpcn", 36))
        draw.text(((result.width - character_name_width)//2, 72), character_name, (80,80,80), get_font("grpcn", 45))
        return result
    
    async def make_illustration(self, _data: dict, card_id: int) -> Image.Image:
        rarity: int = _data["rarity"]
        attribute: str = _data["attribute"]
        frame: Image.Image = data.card.frame_large_img[str(rarity) if rarity != 1 else f"{rarity}_{attribute}"].resize((860, 576), Image.Resampling.BILINEAR).convert("RGBA")
        attribute: Image.Image = data.card.attribute_img[_data["attribute"]].resize((83, 83), Image.Resampling.BILINEAR)
        illusts = await data.card.get_res(card_id)

        result = Image.new("RGBA", (1006, 560 * len(illusts) + 48 * (len(illusts) - 1) + 32), (255,255,255))
        for i, k in enumerate(illusts):
            type, illust = k, illusts[k].resize((840, 630), Image.Resampling.BICUBIC).crop((0, 35, 840, 595))
            result.paste(illust, (81, 24 + (illust.height + 48) * i), illust.split()[3])
            result = ImageUtils.paste(result, frame, (81 - 6, 24 + (illust.height + 48) * i - 6))
            result = ImageUtils.paste(result, attribute, (illust.width - 4, 31 + (illust.height + 48) * i))
            star = data.card.star_img.resize((60, 60), Image.Resampling.BILINEAR) if type == "trained" else data.card.star_normal_img.resize((60, 60), Image.Resampling.BILINEAR)
            for j in range(0, rarity):
                result = ImageUtils.paste(result, star, (84, illust.height - 60 * j - 38 + (illust.height + 48) * i))
        return result

    async def make_power(self, card_id: int):
        power = await data.card.get_max_stat(card_id)

        result: Image.Image = Image.open(os.path.abspath(f'./data/card/res/power.png')).convert("RGBA")
        draw = ImageDraw.Draw(result)
        draw.text((724, 11), str(power['total']), (80,80,80), get_font("grpjp", 45))
        draw.text((59, 146), str(power['performance']), (85,85,85), get_font("grpjp", 30))
        draw.text((375, 146), str(power['technique']), (85,85,85), get_font("grpjp", 30))
        draw.text((703, 146), str(power['visual']), (85,85,85), get_font("grpjp", 30))
        return result

    async def make_character_level(self, card_id: int):
        level = await data.card.get_level_limit(card_id)
        result: Image.Image = Image.open(os.path.abspath(f'./data/card/res/player_level.png')).convert("RGBA")
        draw = ImageDraw.Draw(result)
        draw.text((92, 75), str(level), (95,95,95), get_font("grpjp", 36))
        draw.text((184, 83), str(level), (95,95,95), get_font("grpjp", 28))
        return result
    
    async def make_released_time(self, _data: dict) -> Image.Image:
        released_text = "\n".join([await self.timestamp_to_datetime(i) + [" (JP)", " (EN)", " (TW)", " (CN)", " (KR)"][idx] for idx, i in enumerate(_data["releasedAt"]) if (i and idx in [0, 3]) or (i and idx == 2 and not _data["releasedAt"][JP])])
        return ImageUtils.paste(Image.open(os.path.abspath(f'./data/card/res/released_time.png')).crop((0, 0, 1006, 72 + 40 * (released_text.count("\n") + 1))).convert("RGBA"),
                                ImageUtils.text2img(released_text,
                                    {
                                        "width": 1006,
                                        "x_padding": 0,
                                        "y_padding": 0,
                                        "fill": (81, 81, 81),
                                        "bg_fill": (0, 0, 0, 0),
                                        "font": get_font("grpcn", 30)
                                    }),
                                    (45, 69)
                                )
    
    async def make_skill_level(self):
        result: Image.Image = Image.open(os.path.abspath(f'./data/card/res/skill_level.png')).convert("RGBA")
        draw = ImageDraw.Draw(result)
        draw.text((92, 75), "5", (95,95,95), get_font("grpjp", 36))
        draw.text((154, 83), "5", (95,95,95), get_font("grpjp", 28))
        return result

    async def make_skill(self, card_id: int):
        return ImageUtils.paste(Image.open(os.path.abspath(f'./data/card/res/skill_description.png')).convert("RGBA"), 
                                ImageUtils.text2img(
                                    await data.skill.get_skill_description(str(await data.card.get_skill_id(card_id))), 
                                    {
                                    "width": 1006,
                                    "x_padding": 73,
                                    "y_padding": 27,
                                    "fill": (81, 81, 81),
                                    "bg_fill": (0, 0, 0, 0),
                                    "font": get_font("grpcn", 32)
                                }), 
                                (0, 0)
                            ) 

    async def get_card(self, id: int) -> Image.Image:
        _data: dict = await data.card.get_data(id)
        
        imgs = []
        imgs.append(await self.make_title(_data))
        imgs.append(await self.make_illustration(_data, id))
        imgs.append(await self.make_power(id))
        imgs.append(await self.make_released_time(_data))
        imgs.append(await self.make_character_level(id))
        imgs.append(await self.make_skill_level())
        imgs.append(await self.make_skill(id))

        img = ImageUtils.merge_images(imgs, "v", 16, 0, 32, (255, 255, 255, 255))
        draw = ImageDraw.Draw(img)

        ImageUtils.border_text(draw, (4, img.height - 28), "ID " + str(id), get_font("grpjp", 24), (0,0,0), (255,255,255))

        base = ImageUtils.add_circle_corn(img, 16, frame_width=1, frame_color=(240, 240, 240))

        bg = ImageUtils.merge_images((await data.card.get_res(id)).values(), "v", 0, 0, 0).resize((base.width + 64, 1334 // 1002 * base.width), Image.Resampling.BICUBIC)
        
        result = Image.new("RGBA", (base.width + 64, base.height + 64), (255, 255, 255))

        for i in range(0, base.height // bg.height + 1):
            result.paste(bg, (0, bg.height * i))
        
        return ImageUtils.paste(result.filter(ImageFilter.GaussianBlur(radius=4)), base, (32, 32))
    
    async def adjust_list(self, obj):
        """
        将对象调整为长宽比接近1的嵌套列表对象。
        如果对象只有一行或一列，将其转换为行列数尽可能接近的二维列表。
        """
        rows = len(obj)
        cols = len(obj[0])
        
        if rows == 1:  # 如果只有一行
            # 计算最优的列数，使得长宽比接近1
            new_cols = int(round(cols ** 0.5))
            while cols % new_cols != 0:
                new_cols -= 1
            # 根据新列数重组列表
            new_obj = [obj[0][i:i+cols//new_cols] for i in range(0, cols, cols//new_cols)]
        elif cols == 1:  # 如果只有一列
            # 计算最优的行数，使得长宽比接近1
            new_rows = int(round(rows ** 0.5))
            while rows % new_rows != 0:
                new_rows -= 1
            # 根据新行数重组列表
            new_obj = [[obj[i][0] for i in range(r, r+rows//new_rows)] for r in range(0, rows, rows//new_rows)]
        else:  # 如果不止一行一列，不需要调整
            new_obj = obj
        
        return new_obj

    async def sort_cards(self, card_ids: list) -> list:
        attribute_order = ["cool", "happy", "powerful", "pure"]
        result = []
        
        character_ids = []
        for i in card_ids:
            character_id = await data.card.get_character_id(i)
            if character_id not in character_ids:
                character_ids.append(character_id)
        character_ids.sort()
        
        if len(character_ids) == 1:
            # 单人按属性排
            for attribute in attribute_order:
                filtered_list = [card_id for card_id in card_ids if await data.card.get_attribute(card_id) == attribute]
                sorted_list = await self.sort_filtered_list(filtered_list)
                for idx, v in enumerate(sorted_list):
                    sorted_list[idx] = await self.init_thumb(card_id=v)
                if sorted_list:
                    result.append(sorted_list)
        elif len(character_ids) > 5:
            # 5人以上按乐团排
            group_size = 5
            num_groups = (len(character_ids) + group_size - 1) // group_size
            
            for group_index in range(num_groups):
                start_index = group_index * group_size
                end_index = (group_index + 1) * group_size
                
                current_list = []
                for card_id in card_ids:
                    char_id = await data.card.get_character_id(card_id)
                    if char_id in character_ids[start_index:end_index]:
                        current_list.append(card_id)
                
                if current_list:
                    sorted_list = await self.sort_filtered_list(current_list)
                    for idx, v in enumerate(sorted_list):
                        sorted_list[idx] = await self.init_thumb(card_id=v)
                    result.append(sorted_list)
        else:
            # 2-5人按角色和属性排
            for attribute in attribute_order:
                for i in range(1, 36):
                    filtered_list = [card_id for card_id in card_ids if await data.card.get_character_id(card_id) == i and await data.card.get_attribute(card_id) == attribute]
                    sorted_list = await self.sort_filtered_list(filtered_list)
                    for idx,v in enumerate(sorted_list):
                        sorted_list[idx] = await self.init_thumb(card_id=v)
                    if sorted_list:
                        result.append(sorted_list)
        return await self.adjust_list(result)
        
    async def sort_filtered_list(self, filtered_list):
        async def get_rarity(x):
            return await data.card.get_rarity(x)

        tasks = [get_rarity(x) for x in filtered_list]
        rarities = await asyncio.gather(*tasks)

        sorted_list = [x for _, x in sorted(zip(rarities, filtered_list), reverse=True)]

        return sorted_list

    async def get(self, prompt: str) -> Image.Image:
        prompts = prompt[2:].strip().split()

        if len(prompts) == 1 and prompts[0].isdigit():
            result = await self.get_card(prompts[0])
        else:
            cfg = {
                "attribute": [],
                "bandId": [],
                "rarity": [],
                "type": [],
                "characterId": []
            }
            for i in prompts:
                if i in data.card.attribute_list:
                    cfg["attribute"] += await data.card.get_attribute_types(i)
                elif i in data.card.band_list:
                    cfg["bandId"] += await data.card.get_band_ids(i)
                elif i in data.card.rarity_list:
                    cfg["rarity"] += await data.card.get_rarities(i)
                elif i in data.card.type_list:
                    cfg["type"] += await data.card.get_types(i)
                else:
                    cfg["characterId"] += await data.card.get_character_ids(i)
            result = await self.get_cards(cfg.get("characterId"), cfg.get("bandId"), cfg.get("attribute"), cfg.get("rarity"), cfg.get("type"))
        # result.paste(data.card.watermark, box=(result.getbbox()[2] - 193, result.getbbox()[3] - 24), mask=data.card.watermark.split()[3])
        return result

card = Card()


class PlayerState(object):
    def __init__(self) -> None:
        self.font_path = os.path.abspath("data/fonts/GB18030.ttf")
        logger.info("STATE: 字体加载成功")

        self.servers = ["jp", "en", "tw", "cn", "kr"]
        self.servers_dict = {
            "jp": 0,
            "en": 1,
            "tw": 2,
            "cn": 3,
            "kr": 4
        }
        self.music_nickname2bdname = {
            "cleared": "clearedMusicCountMap",
            "full_combo": "fullComboMusicCountMap",
            "all_perfect": "allPerfectMusicCountMap"
        }
        self.degreeTypes = ["score_ranking", "try_clear", "event_point", "normal"]

        self.img_info = Image.open(os.path.abspath(f'./data/bg/info.png')).convert("RGBA")
        self.img_basic_band_info = Image.open(os.path.abspath(f'./data/bg/basic_band_info.png')).convert("RGBA")
        self.img_frame_leader = Image.open(os.path.abspath(f'./data/bg/frame_leader.png')).convert("RGBA")
        self.img_band_rank = Image.open(os.path.abspath(f'./data/bg/band_rank.png')).convert("RGBA")
        self.img_music = {
            "cleared": Image.open(os.path.abspath(f'./data/bg/music_cleared.png')).convert("RGBA"),
            "full_combo": Image.open(os.path.abspath(f'./data/bg/music_full_combo.png')).convert("RGBA"),
            "all_perfect": Image.open(os.path.abspath(f'./data/bg/music_all_perfect.png')).convert("RGBA")
        }
        logger.info("STATE: 资源加载成功")
        
        self.get_data()

        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(self.get_data, 'interval', hours=1)
        self.scheduler.start()
        logger.info("STATE: 添加定时任务成功，将每小时更新一次数据")

    def get_data(self):
        '''
        获取资源/数据
        '''
        url_degree = "https://bestdori.com/api/degrees/all.3.json"
        if USE_CACHE:
            with open(os.path.abspath("./cache/all.3.json"), 'r', encoding="UTF-8") as f:
                self.data_degree: dict = json.load(f)
        else:
            self.data_degree: dict = json.loads(requests.get(url_degree).text)
        logger.info("STATE: 数据获取成功")

        self.res_jp_degree, self.res_cn_degree = [], []
        for v in self.data_degree.values():
            if v["baseImageName"][JP]:
                self.res_jp_degree.append(v["baseImageName"][JP] + ".png")
            if v["baseImageName"][CN]:
                self.res_cn_degree.append(v["baseImageName"][CN] + ".png")
        self.miss_jp_degrees = list(set(self.res_jp_degree).difference(set(self.get_file_name(os.path.abspath(f'./data/degrees/jp')))))
        self.miss_cn_degrees = list(set(self.res_cn_degree).difference(set(self.get_file_name(os.path.abspath(f'./data/degrees/cn')))))

        if len(self.miss_jp_degrees) > 0 :
            logger.warning(f"STATE: 称号资源(JP)未下载: {self.miss_jp_degrees}")
            logger.info("STATE: 开始尝试下载称号资源(JP)")
            download.download_degrees(self.miss_jp_degrees, "jp")
        else:
            logger.info("STATE: 称号资源(JP)加载成功")

        if len(self.miss_cn_degrees) > 0 :
            logger.warning(f"STATE: 称号资源(CN)未下载: {self.miss_cn_degrees}")
            logger.info("STATE: 开始尝试下载称号资源(CN)")
            download.download_degrees(self.miss_cn_degrees, "cn")
        else:
            logger.info("STATE: 称号资源(CN)加载成功")

    def to_width(self, string: str, font: ImageFont.ImageFont) -> int:
        return math.ceil(font.getlength(string))

    def get_file_name(self, file_dir):
        names = []
        for root, dirs, files in os.walk(file_dir):
            names += files
        return names
    
    def make_degree(self, degreeId: str, server: int) -> Image.Image:
        '''
        绘制牌子
        '''
        rank = self.data_degree[degreeId]["rank"][server] if self.data_degree[degreeId]["rank"][server] != "none" else "rank_none"

        baseImageName = self.data_degree[degreeId]["baseImageName"][server]

        # 这一坨有点难处理，先放着，我怕动了跑不了了
        if self.data_degree[degreeId]["iconImageName"][server] != "none" and self.data_degree[degreeId]["iconImageName"][server] is not None:
            iconImageName = self.data_degree[degreeId]["iconImageName"][server] 
        else:
            iconImageName = "icon_none"
        if iconImageName.startswith("medley") and rank not in ["1", "2", "3"]:
            iconImageName = iconImageName.split("_", 1)[0]
        elif iconImageName.startswith("opening"):
            if rank in ["1", "2", "3"]:
                iconImageName += rank
            else:
                iconImageName
        elif iconImageName.startswith("event_point_icon"):
            iconImageName = self.data_degree[degreeId]["degreeType"][server] + "_" + rank

        rankName = "rank_none"
        for degreeType in self.degreeTypes:
            if self.data_degree[degreeId]["degreeType"][server] == degreeType and self.data_degree[degreeId]['rank'][server] != "none":
                if degreeType != "normal":
                    rankName = f"{degreeType}_{self.data_degree[degreeId]['rank'][server]}"
                break

        baseImage: Image.Image = Image.open(os.path.abspath(f'./data/degrees/{self.servers[server]}/{baseImageName}.png')).convert("RGBA")
        iconImage: Image.Image = Image.open(os.path.abspath(f'./data/degrees/{self.servers[server]}/{iconImageName}.png')).convert("RGBA")
        rankImage: Image.Image = Image.open(os.path.abspath(f'./data/degrees/{self.servers[server]}/{rankName}.png')).convert("RGBA")
        baseImage = ImageUtils.paste(baseImage, rankImage, (0, 0))
        baseImage = ImageUtils.paste(baseImage, iconImage, (0, 0))
        return baseImage

    async def make_info_img(self, _data: dict, type: str) -> Image.Image:
        '''
        绘制玩家简介
        '''
        im = Image.new("RGBA", (self.img_info.width, self.img_info.height))
        im.paste(self.img_info, (0,0), self.img_info.split()[3])
        isTrained = _data["data"]["profile"]["userProfileSituation"]["illust"] != "normal"
        card_id = _data["data"]["profile"]["userProfileSituation"]["situationId"]
        thumb_imgs = await data.card.get_thumb_res(card_id)
        for i, j in thumb_imgs.items():
            if (i == "trained") == isTrained:
                thumb_card = j
        thumb_card = (await card.make_thumb_card(card_id, thumb_card, isTrained)).convert("RGBA").resize((110, 110), Image.Resampling.LANCZOS)
        im.paste(thumb_card, (39, 36), thumb_card.split()[3])
        font = ImageFont.truetype(font=self.font_path, size = 48)
        font_28 = ImageFont.truetype(font=self.font_path, size = 28)
        draw = ImageDraw.Draw(im)
        draw.text(((448 - self.to_width("等级", font_28))//2, 50), "等级", (81,81,81), font_28)
        draw.text(((448 - self.to_width(str(_data["data"]["profile"]["rank"]), font))//2, 63+8), str(_data["data"]["profile"]["rank"]), (81,81,81), font)
        draw.text((316, 56), _data["data"]["profile"]["userName"], (81,81,81), font)
        draw.text((260, 287), _data["data"]["profile"]["introduction"], (81,81,81), font_28)
        degrees = []
        degrees.append(self.make_degree(str(_data["data"]["profile"]["userProfileDegreeMap"]["entries"]["first"]["degreeId"]), self.servers_dict[type]).resize((401, 87), Image.Resampling.LANCZOS))
        if _data["data"]["profile"]["userProfileDegreeMap"]["entries"].get("second"):
            degrees.append(self.make_degree(str(_data["data"]["profile"]["userProfileDegreeMap"]["entries"]["second"]["degreeId"]), self.servers_dict[type]).resize((401, 87), Image.Resampling.LANCZOS))
        for i,v in enumerate(degrees):
            im = ImageUtils.paste(im, v, (40 + i * 417, 164))
        return im.crop((0, 36, 1086, 347))
    
    async def make_simple_info_img(self, _data: dict, type: str) -> Image.Image:
        '''
        用于在没有详细玩家信息时绘制简介
        '''
        im = Image.new("RGBA", (self.img_info.width, self.img_info.height))
        im.paste(self.img_info, (0,0), self.img_info.split()[3])
        thumb_card = (await card.make_thumb_card(1, (await data.card.get_thumb_res(1))["normal"], False)).convert("RGBA").resize((110, 110), Image.Resampling.LANCZOS)
        im.paste(thumb_card, (39, 36), thumb_card.split()[3])
        font = ImageFont.truetype(font=self.font_path, size = 48)
        font_28 = ImageFont.truetype(font=self.font_path, size = 28)
        draw = ImageDraw.Draw(im)
        draw.text(((448 - self.to_width("等级", font_28))//2, 50), "等级", (81,81,81), font_28)
        draw.text(((448 - self.to_width(str(_data["data"]["profile"]["rank"]), font))//2, 63+8), str(_data["data"]["profile"]["rank"]), (81,81,81), font)
        draw.text((316, 56), _data["data"]["profile"]["userName"], (81,81,81), font)
        draw.text((260, 287), _data["data"]["profile"]["introduction"], (81,81,81), font_28)
        degreeImage = self.make_degree(str(_data["data"]["profile"]["degree"]), self.servers_dict[type]).resize((401, 87), Image.Resampling.LANCZOS)
        im = ImageUtils.paste(im, degreeImage, (40, 164))
        return im
    
    async def make_total_desk_power_img(self, _data: dict) -> Image.Image:
        '''
        绘制乐队图片
        '''
        im = Image.new("RGBA", (self.img_basic_band_info.width, self.img_basic_band_info.height))
        im.paste(self.img_basic_band_info, (0,0), self.img_basic_band_info.split()[3])
        font_36 = ImageFont.truetype(font=self.font_path, size = 36)
        font_26 = ImageFont.truetype(font=self.font_path, size = 26)
        card_stats, areaitem_dict = {}, {}

        for i in _data["data"]["profile"]["mainDeckUserSituations"]["entries"]:
            card_stats[i["situationId"]] = await data.card.get_level_stat(i["situationId"], str(i["level"]), i["trainingStatus"] == "done")

        for i in _data["data"]["profile"]["enabledUserAreaItems"]["entries"]:
            areaitem_dict[str(i["areaItemCategory"])] = str(i["level"])

        final_stat = await data.calculate_final_stat(card_stats, areaitem_dict)

        draw = ImageDraw.Draw(im)
        draw.text((908, 34-28), str(int(final_stat["total"])), (255,255,255), font_36)
        cards = _data["data"]["profile"]["mainDeckUserSituations"]["entries"]
        cards[0], cards[1], cards[2], cards[3] = cards[3], cards[1], cards[0], cards[2]

        for i,v in enumerate(cards):
            thumb: Image.Image = (await card.extra_get_thumb_card(str(v["situationId"]), v["illust"], v["trainingStatus"])).resize((189,189), Image.Resampling.BILINEAR)
            thumb = ImageUtils.paste(thumb, data.card.level_img, (thumb.width - 8 - data.card.level_img.width, thumb.height - 8 - data.card.level_img.height))
            draw_thumb = ImageDraw.Draw(thumb)
            draw_thumb.text((149, 151), str(v["level"]), (254,254,254), font_26)
            im.paste(thumb, (42 + 202*i, 96-28), thumb.split()[3])
        im.paste(self.img_frame_leader, (441, 90-28), self.img_frame_leader.split()[3])
        return im
    
    async def make_band_rank_img(self, _data: dict) -> Image.Image:
        '''
        绘制乐队等级
        '''
        im = Image.new("RGBA", (self.img_band_rank.width, self.img_band_rank.height))
        im.paste(self.img_band_rank, (0,0), self.img_band_rank.split()[3])
        font_32 = ImageFont.truetype(font=self.font_path, size=32)
        draw = ImageDraw.Draw(im)
        for i,v in enumerate(["1", "2", "4", "5", "3"]):
            level = str(_data["data"]["profile"]["bandRankMap"]["entries"][v])
            draw.text((94+(45-self.to_width(level, font_32))//2 + i*213, 153), level, (80,80,80), font_32)
        for i,v in enumerate(["21", "18"]):
            level = str(_data["data"]["profile"]["bandRankMap"]["entries"][v])
            draw.text((94+(45-self.to_width(level, font_32))//2 + i*213, 279), level, (80,80,80), font_32)
        return im
    
    async def make_music_img(self, data: dict, type: str) -> Image.Image:
        '''
        绘制歌曲信息
        '''
        im = Image.new("RGBA", (self.img_music[type].width, self.img_music[type].height))
        im.paste(self.img_music[type], (0,0), self.img_music[type].split()[3])
        font_32 = ImageFont.truetype(font=self.font_path, size=32)
        sum = 0
        draw = ImageDraw.Draw(im)
        for i,v in enumerate(["easy", "normal", "hard", "expert", "special"]):
            if not data["data"]["profile"][self.music_nickname2bdname[type]].get("entries"):
                data["data"]["profile"][self.music_nickname2bdname[type]]["entries"] = {"special": "0","normal": "0","expert": "0","hard": "0","easy": "0"}
            num = data["data"]["profile"][self.music_nickname2bdname[type]]["entries"][v] if data["data"]["profile"][self.music_nickname2bdname[type]]["entries"].get(v) else "0"
            draw.text((42+(170-self.to_width(num, font_32))//2+sum, 144), num, (80,80,80), font_32)
            if i == 1 or i == 3:
                sum += 206 
            else:
                sum += 210
        return im

    async def trans_jp_music_to_cn(self, jp_dict: dict):
        '''
        用于日服歌曲信息到国服的转换
        '''
        cleared_count_map = {}
        combo_count_map = {}
        perfect_count_map = {}

        for level in ["special", "normal", "expert", "hard", "easy"]:
            data = jp_dict["userMusicClearInfoMap"]["entries"].get(level, {})
            if not data:
                data = {
                    "clearedMusicCount": 0,
                    "fullComboMusicCount": 0,
                    "allPerfectMusicCount": 0
                }
            cleared_count_map[level] = str(data.get("clearedMusicCount", 0))
            combo_count_map[level] = str(data.get("fullComboMusicCount", 0))
            perfect_count_map[level] = str(data.get("allPerfectMusicCount", 0))

        return {
            "clearedMusicCountMap": {"entries": cleared_count_map},
            "fullComboMusicCountMap": {"entries": combo_count_map},
            "allPerfectMusicCountMap": {"entries": perfect_count_map}
        }

    async def init_img(self, uid: str, _data: dict, type: str) -> Image.Image:
        '''
        初始化图片
        `uid`: 玩家ID
        `_data`: API请求下来的数据
        `type`: cn/jp
        '''
        imgs = []
        if _data["data"]["profile"].get("userProfileSituation") and _data["data"]["profile"].get("userProfileDegreeMap"):
            imgs.append(await self.make_info_img(_data, type))
        else:
            imgs.append(await self.make_simple_info_img(_data, type))
        if _data["data"]["profile"]["publishTotalDeckPowerFlg"]:
            imgs.append(await self.make_total_desk_power_img(_data))
        if _data["data"]["profile"]["publishBandRankFlg"]:
            imgs.append(await self.make_band_rank_img(_data))
        if type == "jp":
            music__data = await self.trans_jp_music_to_cn(_data["data"]["profile"])
            if music__data.get("clearedMusicCountMap"):
                _data["data"]["profile"]["clearedMusicCountMap"] = music__data.get("clearedMusicCountMap")
            if music__data.get("fullComboMusicCountMap"):
                _data["data"]["profile"]["fullComboMusicCountMap"] = music__data.get("fullComboMusicCountMap")
            if music__data.get("allPerfectMusicCountMap"):
                _data["data"]["profile"]["allPerfectMusicCountMap"] = music__data.get("allPerfectMusicCountMap")
        if _data["data"]["profile"]["publishMusicClearedFlg"]:
            imgs.append(await self.make_music_img(_data, "cleared"))
        if _data["data"]["profile"]["publishMusicFullComboFlg"]:
            imgs.append(await self.make_music_img(_data, "full_combo"))
        if _data["data"]["profile"]["publishMusicAllPerfectFlg"]:
            imgs.append(await self.make_music_img(_data, "all_perfect"))

        result = ImageUtils.merge_images(imgs, "v", 8, 0, 32, (255, 255, 255, 255))
        draw = ImageDraw.Draw(result)

        dt = datetime.datetime.fromtimestamp(_data['data']['time'] / 1000)
        time_str = dt.strftime("%m/%d %H:%M")

        info = f"UID {uid} | CACHE {_data['data']['cache']} | TIME {time_str} ({type.upper()})"
        ImageUtils.border_text(draw, (4, result.height - 30), info, ImageFont.truetype(font=self.font_path, size = 24), (50,50,50), (255,255,255))
        return result
    
    async def get(self, uid: str, type: str) -> Image.Image:
        '''
        `uid`: 玩家ID
        `type`: cn/jp
        '''
        url = f"https://bestdori.com/api/player/{type}/{uid}?mode=2"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                _data = await response.text()
                _data = json.loads(_data)
        result = await self.init_img(uid, _data, type)
        result.paste(data.card.watermark, box=(result.getbbox()[2] - 193, result.getbbox()[3] - 24), mask=data.card.watermark.split()[3])
        return result

player_state = PlayerState()

