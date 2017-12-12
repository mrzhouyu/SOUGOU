#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2017/12/11 8:08
# @Author  : Yu
# @Site    : 
# @File    : spider.py

import requests
import time
from requests.exceptions import ConnectionError
from pyquery import PyQuery as pq
import pymongo
from config import *
#初始代理为None
proxy=None
#每个index 的requests请求最大次数
max_times=5


con=pymongo.MongoClient(MONGODB_HOST)
db=con[MONGODB_DB]

#用来判断是否返回异常页面的url

#cookie和头
#这里的cookie每次执行必须保持页面已经登陆 用自己登陆的cookie 注意更新
header = {
    'Cookie': 'IPLOC=CN3508; SUID=DB75CE792613910A000000005A196A54; ld=8Zllllllll2z4LhnlllllVoKbwclllllWtiCGlllll9lllll4klll5@@@@@@@@@@; SUV=00DF71D679CE75305A1F6C91B7570613; LSTMV=212%2C184; LCLKINT=3437; SNUID=0476CC7A0307620E0ED5D71303161850; ABTEST=5|1512979763|v1; weixinIndexVisited=1; sct=2; JSESSIONID=aaadGi88QKDY2_ICQOv8v; ppinf=5|1512983255|1514192855|dHJ1c3Q6MToxfGNsaWVudGlkOjQ6MjAxN3x1bmlxbmFtZTo2Oll1Q2hvdXxjcnQ6MTA6MTUxMjk4MzI1NXxyZWZuaWNrOjY6WXVDaG91fHVzZXJpZDo0NDpvOXQybHVGaXFMTzBweU1wcE5QcFVoTVVpQ3ZVQHdlaXhpbi5zb2h1LmNvbXw; pprdig=p1XUo1F81DesSE92cLfzc4hIA3LXo-jnBYEfUEvOpOo5UNi2kDxOTkMULAXHIFloocHlIKXDKV9wZ5fuMtMJ0HtV9cw-WDyAYeqBWtXDebv5B4Nq_mb1K1GdlySarzWqiY__1Lpw66qvQ0VCQ7rjQLJrOCMgNZbr_qYDeMqrdo4; sgid=12-32444531-AVouSte4AIJ1gpCWLUrUKTQ; ppmdig=1512983255000000e9e388e2144c781071fedac61456b7c2',
    'Host': 'weixin.sogou.com',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36',
}
#获取代理 这里用到来自https://github.com/Germey/ProxyPool-master的一个代理池
#本地5000端口获取IP地址
proxy_url='http://localhost:5000/get'
def get_proxy():
    try:
        ip=requests.get(proxy_url)
        if ip.status_code==200:
            return ip.text
        return None
    except:
        print('无法获取代理....')
        return None

#index请求和代理
def request_fun(url,params,times=1):
    spider_url = 'http://weixin.sogou.com/antispider'
    print("当前请求次数：",times)
    if times>=5:
        return None
    elif times>1:
        print('重新请求..')
    global proxy
    try:
        if proxy:
            proxies={
                'http':'http'+proxy
            }
            req = requests.get(url, params=params, headers=header,proxies=proxies)
        else:
            req = requests.get(url, params=params, headers=header)
        req.encoding=req.apparent_encoding

        if req.url[0:34]==spider_url:
                print('返回异常连接','需要使用代理，获取代理')
                proxy=get_proxy()
                if proxy:
                    print('Using Proxy:',proxy)
                    request_fun(url,params)
                else:
                    print('Get Proxy Faild')
        if req.status_code==200:
            print("当前请求url:", req.url)
            return req.text
    except ConnectionError:
        print("连接异常")
        times+=1
        return request_fun(url,params,times)


#得到首页源代码并且解析
def get_index_page(keyword,page):
    url='http://weixin.sogou.com/weixin?'
    data={
        'query':keyword,
        'type': 2,
        'page':page
    }
    index_html=request_fun(url,data)
    parser_index__return_articleurl(index_html)

#index解析并且直接调用article请求函数
def parser_index__return_articleurl(html1):
    doc=pq(html1)
    ul=doc('#main .news-box .news-list')
    items=ul('li').items()
    for li in items:
        h3=li('div.txt-box').find('h3').items()
        for a in h3:
            article_url=a('a').attr('href')
            #得到的文章url传入文章解析函数
            article_requests(article_url)


#文章请求函数
def article_requests(url):
    print('当前文章页面url:',url)
    try:
        response=requests.get(url)
        response.encoding=response.apparent_encoding
        if response.status_code==200:
            print("当前文章页面返回正常")
            article_html=response.text
            #调用文章解析函数解析网页
            article_parser(article_html)
    except:
        return article_requests(url)

#文章解析函数
def article_parser(html):
    doc=pq(html)
    page_content=doc('div#page-content').find('div#img-content')
    for content in page_content.items():
        #数据清洗和存储
        contents={
            'title':content('h2').text().strip(),
            'time':content('div#meta_content').find('em').text().split(' ')[0],
            'name':content('div#meta_content').find('a').text(),
            'content':content('div.rich_media_content').text()
        }
        #这里的输出用于调试
        print(contents)
        #存入数据库
        save_mongodb(contents)

#保存到数据库
def save_mongodb(content):
    #如果存在该title则执行更新
    if db[MONGODB_TABLE].update({'title':content['title']},{'$set':content},True):
        print('该文章存储完毕...')
    else:
        print('数据存储出错...')

def main():
    for page in range(1,101):
        get_index_page(KEY_WORD,page)


if __name__=='__main__':
    start_time=time.time()
    main()
    print('总共花费：{}s'.format(time.time()-start_time))
