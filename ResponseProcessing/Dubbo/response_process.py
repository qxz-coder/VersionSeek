# This script is used to parse the response from the server
import os,re,json
from difflib import SequenceMatcher


# 模糊文本
def mask_text(fileContent: str):
    '''Mask processing based on regular matching
    
    Args:
        fileContent: Original response string
        
    Returns:
        response: Response string after noise reduction processing
    '''
    
    # ip mask: 192.168.x.x--> 192.0.0.0 172.3x.0.0-->172.0.0.0
    response = fileContent
    ipPattern = '(192\.168\.\d+\.\d+)|(172\.\d+\.\d+\.\d+)'
    ipRes = re.findall(ipPattern, response, re.I)
    # print(ipRes)
    for a, b in set(ipRes):
        ip = a if len(a) else b
        # print(ip)
        iphead = ip.split('.')[0]
        # if ip1 and len(ip1):
        response = response.replace(ip, f'{iphead}.0.0.0')

    # !!!! resource mask: load；0.4877---> load: 0.0 ,cpu:4---> cpu:1  attention plz!!!!!!!!!!!!
    
    loadPattern = '(load:(0\.\d+),cpu:(\d+))'
    loadRes = re.findall(loadPattern, response, re.I)
    for a,b,c in set(loadRes):
        length=len(a)
        response=response.replace(a,'load:1,cpu:1'.ljust(length,' '))
    # loadPattern = '(load:0\.\d+)|(cpu:\d+)'
    # loadRes = re.findall(loadPattern, response, re.I)
    # # print(loadRes)
    # for a, b in set(loadRes):
    #     load = a if len(a) else b
    #     # print(load)
    #     loadHead = load.split(':')[0]
    #     # if ip1 and len(ip1):
    #     response = response.replace(load, f'{loadHead}:1')

    # memory mask: max:1964M,total:126M,used:55M,free:71M  --> max:10M,totol:10M,used:10M,free:10M  clients:1->clients:0
    memoryPattern = '(max:\d+M,total:\d+M,used:\d+M,free:\d+M)|(clients:\d+)'         # max:1964M,total:175M,used:96M,free:79M
    memoryRes = re.findall(memoryPattern, response, re.I)
    # print(memoryRes)
    for a, b in memoryRes:
        if a:
            response = response.replace(a, 'max:10M,total:10M,used:10M,free:10M'.ljust(len(a),' '))
        if b:
            response = response.replace(b, 'clients:0')

    # ls state mask:
    # timestamp=1682660709019 ---> timestamp=1600000000000
    # className mask:    com.alibaba.dubbo.demo.DemoService, org.apache.dubbo.samples.api.client.HelloService org.apache.dubbo.samples.api.GreetingsService-> m1.m2.Demo
    # methodName mask:  methods=sayHello
    # application mask: demo-provider,first-dubbo-provider ---> demo-provider
    timeAndApplicaitonPattern = '(timestamp=\d+)|(first-dubbo-provider)'
    timeAndApplicaitonRes = re.findall(
        timeAndApplicaitonPattern, response, re.I)
    # print(timeAndApplicaitonRes)
    for a, b in timeAndApplicaitonRes:
        if a:
            response = response.replace(a, 'timestamp=1600000000000')
        if b:
            response = response.replace(b, 'demo-provider')

    classPattern = '(com\.alibaba[^ ?&]+)|(org\.apache[^ ?&]+)'
    classRes = re.findall(classPattern, response, re.I)
    # print(classRes)
    for a, b in classRes:
        if a:
            response = response.replace(a, 'com.alibaba.Demo')
        if b:
            response = response.replace(b, 'org.apache.Demo')

    methodPattern = '(methods=[^ ?&]+)'
    methodRes = re.findall(methodPattern, response, re.I)
    # print(methodRes)
    for a in methodRes:
        response = response.replace(a, 'methods=testMethod')
    return response


def similarity(text1,text2):
#    from difflib import SequenceMatcher
    return SequenceMatcher(None,text1,text2).ratio()