# ESEBot
 电子科技大学-电子科学与工程学院-研究生自动晚点名QQ机器人

##### 测试群QQ：[945667419](https://jq.qq.com/?_wv=1027&k=b1Jl5mt9)

##### 用法说明: [帮助文档](https://mashiros.top/others/check_help.html)

---

##### 自运行环境:
 windows10 + python3(≥3.7) + [nonebot2](https://github.com/nonebot/nonebot2) + [go-cqhttp](https://github.com/Mrs4s/go-cqhttp) + selenium(firefox)

核心代码在QQBot/qqbot/plugins/night_check文件夹下。写到最后的晚点名服务可以写在另一个模块，但还是偷懒了，*\__init__.py*文件内的代码就显得臃肿了 :(

---

##### 实现思路：
晚点名链接每日都会变，所以无法自动定时点名提交，所以就想到用QQ机器人监听通知群的晚点名链接。再顺手利用nonebot的框架写了一个服务教研室同学的自动晚点名机器人插件。
