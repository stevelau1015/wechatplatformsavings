# -*- coding: utf-8 -*-
import logging
import logging.handlers
from selenium import webdriver
import time
import json
import requests
import re
import random
import os
import sys


import pdfkit


from loggerr import Logger

fh = logging.handlers.TimedRotatingFileHandler('./logs/http-info.log', when='midnight', backupCount=7, encoding='utf8')
logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    level=logging.DEBUG,
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[fh],
)

static_path = os.path.join(os.path.dirname(__file__), "static")

# 微信公众号账号
from selenium.webdriver.common.by import By

user = "email"
# 公众号密码
password = "pwd"
# 设置要爬取的公众号列表
gzlist = ['沙漏狗shallowdog','某公众号','三童','利维坦']
print(gzlist)


# 登录微信公众号，获取登录之后的cookies信息，并保存到本地文本中
def weChat_login():
    # 定义一个空的字典，存放cookies内容
    try:

        post = {}

        # 用webdriver启动谷歌浏览器
        print("启动浏览器，打开微信公众号登录界面")
        CHROME_DRIVER = r"./chromedriver"
        driver = webdriver.Chrome(executable_path=CHROME_DRIVER)
        # 打开微信公众号登录页面
        driver.get('https://mp.weixin.qq.com/')

        # 拿手机扫二维码！
        print("请拿手机扫码二维码登录公众号")
        time.sleep(25)
        print("登录成功")
        # 重新载入公众号登录页，登录之后会显示公众号后台首页，从这个返回内容中获取cookies信息
        driver.get('https://mp.weixin.qq.com/')
        # 获取cookies
        cookie_items = driver.get_cookies()
        print(type(cookie_items))
        print(cookie_items)
        # 获取到的cookies是列表形式，将cookies转成json形式并存入本地名为cookie的文本中
        for cookie_item in cookie_items:
            post[cookie_item['name']] = cookie_item['value']
        print(type(post))
        print(post)

        cookie_str = json.dumps(post)
        print(type(cookie_str))
        print(cookie_str)
        with open('cookie.txt', 'w+', encoding='utf-8') as f:
            f.write(cookie_str)
        print("cookies信息已保存到本地")

    except Exception as error:
        logging.exception(error, exc_info=True)


# 爬取微信公众号文章，并存在本地文本中
def get_content(query):
    # query为要爬取的公众号名称
    # 公众号主页
    url = 'https://mp.weixin.qq.com'
    # 设置headers
    header = {
        "HOST": "mp.weixin.qq.com",
        "User-Agent": "Mozilla/6.0 (Windows NT 6.1; WOW64; rv:53.0) Gecko/20100101 Firefox/53.0"
    }

    # 读取上一步获取到的cookies
    with open('cookie.txt', 'r', encoding='utf-8') as f:
        cookie = f.read()
    cookies = json.loads(cookie)

    # 登录之后的微信公众号首页url变化为：https://mp.weixin.qq.com/cgi-bin/home?t=home/index&lang=zh_CN&token=1849751598，从这里获取token信息
    response = requests.get(url=url, cookies=cookies)
    token = re.findall(r'token=(\d+)', str(response.url))[0]

    # 搜索微信公众号的接口地址
    search_url = 'https://mp.weixin.qq.com/cgi-bin/searchbiz?'
    # 搜索微信公众号接口需要传入的参数，有三个变量：微信公众号token、随机数random、搜索的微信公众号名字
    query_id = {
        'action': 'search_biz',
        'token': token,
        'lang': 'zh_CN',
        'f': 'json',
        'ajax': '1',
        'random': random.random(),
        'query': query,
        'begin': '0',
        'count': '5'
    }
    # 打开搜索微信公众号接口地址，需要传入相关参数信息如：cookies、params、headers
    search_response = requests.get(search_url, cookies=cookies, headers=header, params=query_id)
    # 取搜索结果中的第一个公众号
    lists = search_response.json().get('list')[0]
    # 获取这个公众号的fakeid，后面爬取公众号文章需要此字段
    fakeid = lists.get('fakeid')

    # 微信公众号文章接口地址
    appmsg_url = 'https://mp.weixin.qq.com/cgi-bin/appmsg?'
    # 搜索文章需要传入几个参数：登录的公众号token、要爬取文章的公众号fakeid、随机数random
    query_id_data = {
        'token': token,
        'lang': 'zh_CN',
        'f': 'json',
        'ajax': '1',
        'random': random.random(),
        'action': 'list_ex',
        'begin': '0',  # 不同页，此参数变化，变化规则为每页加5
        'count': '5',
        'query': '',
        'fakeid': fakeid,
        'type': '9'
    }
    # 打开搜索的微信公众号文章列表页
    appmsg_response = requests.get(appmsg_url, cookies=cookies, headers=header, params=query_id_data)
    # 获取文章总数
    max_num = appmsg_response.json().get('app_msg_cnt')
    print("历史文章总数为", max_num)
    print(max_num)
    # 每页至少有5条，获取文章总的页数，爬取时需要分页爬
    num = int(int(max_num) / 5)
    initial = 390
    begin = 27
    while num + 1 > 0:
        query_id_data = {
            'token': token,
            'lang': 'zh_CN',
            'f': 'json',
            'ajax': '1',
            'random': random.random(),
            'action': 'list_ex',
            'begin': '{}'.format(str(begin)),
            'count': '5',
            'query': '',
            'fakeid': fakeid,
            'type': '9'
        }
        print('正在翻页：--------------', begin,'/',max_num)
        print(time.strftime("%Y%m%d-%H%M%S", time.localtime()))
        # 获取每一页文章的标题和链接地址，并写入本地文本中
        query_fakeid_response = requests.get(appmsg_url, cookies=cookies, headers=header, params=query_id_data)
        fakeid_list = query_fakeid_response.json().get('app_msg_list')
        for item in fakeid_list:
            content_link = item.get('link')
            content_title = item.get('title')
            fileName = query

            dirs = './article/'+fileName+'/'

            if not os.path.exists(dirs):
                os.makedirs(dirs)
            pdfkit.from_url(content_link, dirs + content_title + '.pdf')
            print('获取到原创文章：%s ： %s' % (content_title, content_link))
        num -= 1
        begin = int(begin)
        begin += 5
        time.sleep(50)


if __name__ == '__main__':
    try:

        log_path = './Logs/'
        if not os.path.exists(log_path):
            os.makedirs(log_path)
        # 日志文件名按照程序运行时间设置
        log_file_name = log_path + 'log-' + time.strftime("%Y%m%d-%H%M%S", time.localtime()) + '.log'
        # 记录正常的 print 信息
        sys.stdout = Logger(log_file_name)
        # 记录 traceback 异常信息
        sys.stderr = Logger(log_file_name)

        # 登录微信公众号，获取登录之后的cookies信息，并保存到本地文本中
        weChat_login()
        # 登录之后，通过微信公众号后台提供的微信公众号文章接口爬取文章
        for query in gzlist:
            # 爬取微信公众号文章，并存在本地文本中
            print("开始爬取公众号：" + query)
            get_content(query)
            # time.sleep(60)
            print("爬取完成")

    except Exception as e:
        print(str(e))

