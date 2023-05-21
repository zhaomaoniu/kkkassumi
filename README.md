# ToyamaKasumiBot

****
基于 Nonebot2 和 go-cqhttp 开发，是娱乐兼功能型的QQ机器人

## 关于

很多地方都写的不足，以后会慢慢改的。

README.md和部分项目结构参考了 [绪山真寻Bot](https://github.com/nonebot/nonebot2)

（以后香澄的代码都会慢慢传上来）

## 声明

此项目仅用于学习交流，请勿用于非法用途

## 目前

等代码都改完传上来之后会慢慢完善文档，目前仓库里唯一的utils大部分是吉太自己写的

ImageUtils.py是一些关于PIL的utils，BestdoriUtils.py则是基于[Bestdori](https://bestdori.com/)的API的图片生成实现

### ImageUtils的使用

这里不详细讲了，注释写的很清楚

TODO: 给ImageUtils.text2img()加上字间距的参数

### BestdoriUtils的使用

代码里写了爬取Bestdori的资源的Download类，不是很完善，可能需要多下几遍才能爬完所有需要的资源（非Bestdori的资源已经放在仓库里了）

具体使用方法可以参照player_state.get()和player_state.get()的注释，下面是用例

```python
from utils.BestdoriUtils import player_state, card

uid = "1000000000"
server = "cn"

# 获取玩家信息
player_state.get(uid, server).save(f"{uid}.png")

# 获取卡牌信息
player_state.get("查卡 xxxx")
```

## 感谢

[botuniverse / onebot](https://github.com/botuniverse/onebot) ：超棒的机器人协议  
[Mrs4s / go-cqhttp](https://github.com/Mrs4s/go-cqhttp) ：cqhttp的golang实现，轻量、原生跨平台.  
[nonebot / nonebot2](https://github.com/nonebot/nonebot2) ：跨平台Python异步机器人框架  
[HibiKier / zhenxun_bot](https://github.com/HibiKier/zhenxun_bot) : 非常可爱的绪山真寻bot  
[kumoSleeping / xiaoxiaopa](https://github.com/kumoSleeping/xiaoxiaopa) : kumo自主研发的小小趴bot
