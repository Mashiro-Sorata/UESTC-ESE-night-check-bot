from pydantic import BaseSettings



class Config(BaseSettings):
    # Your Config Here
    user_group_id = 1234567     # 用户群QQ号,最好Bot为群主
    target_group_id = 12345678  # 发布每日晚点名通知链接的QQ群的QQ号
    admin_id = 123456789        # Bot管理员QQ号，可以检查Bot风控状态或者手动重启cqhttp
    auto_restart = True         # 设置QQ风控后是否自动重启cqhttp,建议设置为True（当Bot发送消息时报错重启cqhttp.据说以后cqhttp会更改报错机制,代码可能需要重构）
    max_try = 2                 # 风控后错误最大尝试次数,一般2就够了:第一次遇到错误自动重启cqhttp后等待try_sleep后再次发送成功
    try_sleep = 8               # 重启cqhttp后等待try_sleep秒再次发送信息,太短可能会导致cqhttp未重启完成导致消息发送失败
    cmd_dict = {'bind': 'bind 绑定 添加 add update 更改 更新',
                'status': 'status 状态 检查 state',
                'delete': 'delete 删除 注销 remove',
                'help': 'help 帮助 怎么用 ? ？'}
    
    first_choices_pool = {'1': '沙河校区',
                          '2': '清水河校区',
                          '3': '其他'}
    
    second_choices_pool = {
        '1': ({'1': ({}, '23:00前返回宿舍'),
               '2': ({'1': ({}, '教研室会议'),
                      '2': ({}, '科研实验')}, '23:00后返回宿舍')}, '是'),
        '2': ({'1': ({'1': ({}, '回家'),
                      '2': ({}, '因公出差'),
                      '3': ({}, '就医')}, '离校'),
               '2': ({}, '已办理校外住宿手续'),
               '3': ({}, '非全校外住宿')}, '否')}
    
    send_group_msg_url = 'http://127.0.0.1:5700/send_group_msg'
    
    # \n绑定信息：/晚点名 绑定 学号 (选项串) (地址)\n查看状态：/晚点名 状态\n解除绑定：/晚点名 注销
    
    help_str = "\n具体用法：http://mashiros.top/others/check_help.html\n"
    class Config:
        extra = "ignore"

