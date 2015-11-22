#!/usr/bin/python3
#author=zeek
import urllib.request
import socket
import json
import time
import threading
import os
import kmp
import platform

CHATINFOURL = 'http://www.panda.tv/ajax_chatinfo?roomid='
DELIMITER = b'}}'
KMP_TABLE = kmp.kmpTb(DELIMITER)
IGNORE_LEN = 16
FIRST_REQ = b'\x00\x06\x00\x02'
FIRST_RPS = b'\x00\x06\x00\x06'
KEEPALIVE = b'\x00\x06\x00\x00'
RECVMSG = b'\x00\x06\x00\x03'
DANMU_TYPE = '1'
BAMBOO_TYPE = '206'
AUDIENCE_TYPE = '207'
SYSINFO = platform.system()
INIT_PROPERTIES = 'init.properties'



def loadInit():
    with open(INIT_PROPERTIES, 'r') as f:
        init = f.read()
        init = init.split('\n')
        roomid = init[0].split(':')[1]
        #username = init[1].split(':')[1]
        #password = init[2].split(':')[1]
        return roomid


def notify(title, message):
    if SYSINFO == 'Windows':
        pass
    elif SYSINFO == 'Linux':
        os.system('notify-send {}'.format(': '.join([title, message])))
    else:   #for mac
        t = '-title {!r}'.format(title)
        m = '-message {!r}'.format(message)
        os.system('terminal-notifier {} -sound default'.format(' '.join([m, t])))


def getChatInfo(roomid):
    with urllib.request.urlopen(CHATINFOURL + roomid) as f:
        data = f.read().decode('utf-8')
        chatInfo = json.loads(data)
        chatAddr = chatInfo['data']['chat_addr_list'][0]
        socketIP = chatAddr.split(':')[0]
        socketPort = int(chatAddr.split(':')[1])
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((socketIP,socketPort))
        rid      = str(chatInfo['data']['rid']).encode('utf-8')
        appid    = str(chatInfo['data']['appid']).encode('utf-8')
        authtype = str(chatInfo['data']['authtype']).encode('utf-8')
        sign     = str(chatInfo['data']['sign']).encode('utf-8')
        ts       = str(chatInfo['data']['ts']).encode('utf-8')
        msg  = b'u:' + rid + b'@' + appid + b'\nk:1\nt:300\nts:' + ts + b'\nsign:' + sign + b'\nauthtype:' + authtype
        msgLen = len(msg)
        sendMsg = FIRST_REQ + int.to_bytes(msgLen, 2, 'big') + msg
        s.sendall(sendMsg)
        recvMsg = s.recv(4)
        if recvMsg == FIRST_RPS:
            print('成功连接弹幕服务器')
            recvLen = int.from_bytes(s.recv(2), 'big')
        #s.send(b'\x00\x06\x00\x00')
        #print(s.recv(4))
        def keepalive():
            while True:
                #print('================keepalive=================')
                s.send(KEEPALIVE)
                time.sleep(300)
        threading.Thread(target=keepalive).start()

        while True:
            recvMsg = s.recv(4)
            if recvMsg == RECVMSG:
                recvLen = int.from_bytes(s.recv(2), 'big')
                recvMsg = s.recv(recvLen)   #ack:0
                #print(recvMsg)
                recvLen = int.from_bytes(s.recv(4), 'big')
                s.recv(IGNORE_LEN)
                recvLen -= IGNORE_LEN
                recvMsg = s.recv(recvLen)   #chat msg
                #print(recvMsg)
                try:
                    analyseMsg(recvMsg)
                except Exception as e:
                    pass



def analyseMsg(recvMsg):
    position = kmp.kmp(recvMsg, DELIMITER, KMP_TABLE)
    if position == len(recvMsg) - len(DELIMITER):
        formatMsg(recvMsg)
    else:
        preMsg = recvMsg[:position + len(DELIMITER)]
        nextMsg = recvMsg[position + len(DELIMITER) + IGNORE_LEN:]
        formatMsg(preMsg)
        formatMsg(nextMsg)

# pass one audience alert
is_second_audience = False
def formatMsg(recvMsg):
    try:
        jsonMsg = eval(recvMsg)
        content = jsonMsg['data']['content']
        if jsonMsg['type'] == DANMU_TYPE:
            identity = jsonMsg['data']['from']['identity']
            nickName = jsonMsg['data']['from']['nickName']
            if identity == '60':
                nickName = '*房管*' + nickName
            if identity == '90':
                nickName = '*主播*' + nickName
            print(nickName + ":" + content)
            notify(nickName, content)
        elif jsonMsg['type'] == BAMBOO_TYPE:
            nickName = jsonMsg['data']['from']['nickName']
            print(nickName + "送给主播[" + content + "]个竹子")
            notify(nickName, "送给主播[" + content + "]个竹子")
        elif jsonMsg['type'] == AUDIENCE_TYPE:
            global is_second_audience
            if is_second_audience:
                print('===========观众人数' + content + '==========')
                is_second_audience = False
            else:
                is_second_audience = True
        else:
            pass
    except Exception as e:
        pass


def testRoomid(roomid):
    if not roomid:
        roomid = input('roomid:')
        with open(INIT_PROPERTIES, 'r') as f:
            init = f.readlines()
            editInit = ''
            for i in init:
                if 'roomid' in i:
                    i = i[:-1] + str(roomid)
                editInit += i + '\n'
        with open(INIT_PROPERTIES, 'w') as f:
            f.write(''.join(editInit))
    return roomid


def main():
    roomid = loadInit()
    roomid = testRoomid(roomid)
    getChatInfo(roomid)

if __name__ == '__main__':
    main()
