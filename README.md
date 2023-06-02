# ToyamaKasumiBot

****
基于 Nonebot2 和 go-cqhttp 开发，是娱乐兼功能型的QQ机器人

## 关于

很多地方都写的不足，以后会慢慢改的。

README.md和部分项目结构参考了 [绪山真寻Bot](https://github.com/HibiKier/zhenxun_bot)

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

具体使用方法可以参照player_state.get()和player_state.get()的注释，下面是用例(异步函数中直接调用即可)

```python
import asyncio
from utils.BestdoriUtils import data, card, player_state

async def main():
    await data.initialize()
    (await card.get("查卡 1399")).save("cache/temp.png")
    (await player_state.get("1006954716", "cn")).show()


if __name__ == "__main__":
    asyncio.run(main())
```

## 更新日志


### 23/06/03

- 学Tsugu给卡牌详细信息添加了背景
- 修复了无特训卡牌无法查询的bug
- 修复了部分用户玩家状态无法查询的bug
- 移除了水印
- 修复了自动更新没有生效的bug

### 23/05/28

- 修改了BestdoriUtils的结构，现在更方便拓展了
- 玩家状态现在能够精准计算乐队综合力
- 卡牌缩略图现在更像游戏内的了，在左上角加上了乐队图标
- 全部改用异步函数，提升了运行效率（大概？）


## 感谢

[botuniverse / onebot](https://github.com/botuniverse/onebot) ：超棒的机器人协议  
[Mrs4s / go-cqhttp](https://github.com/Mrs4s/go-cqhttp) ：cqhttp的golang实现，轻量、原生跨平台  
[nonebot / nonebot2](https://github.com/nonebot/nonebot2) ：跨平台Python异步机器人框架  
[HibiKier / zhenxun_bot](https://github.com/HibiKier/zhenxun_bot) : 非常可爱的绪山真寻bot  
[kumoSleeping / xiaoxiaopa](https://github.com/kumoSleeping/xiaoxiaopa) : kumo自主研发的小小趴bot   
[Bestdori](https://bestdori.com/) : BanG Dream最大的第三方网站

还有很多群友的帮助！
