# 广州电信接口

import logging
import time
import random
import tornado.gen
import xml.etree.ElementTree as ET
from tornado.httpclient import AsyncHTTPClient, HTTPError

from utils.encryption_decryption import to_md5

request_log = logging.getLogger("madeira.request")

RESULT_MAP = {
    '0': 1,  # 成功
    '1001': 9,  # 数据参数错误
    '1002': 9,  # 请求已过期
    '1003': 9,  # 错误的帐号或者密码
    '1004': 9,  # 错误的客户端 IP 地址
    '1005': 9,  # 接口返回错误
    '9997': 9,  # 客户端连接数超过最大限制
    '9998': 9,  # 系统错误
    '9999': 9,  # 未知错误
}


@tornado.gen.coroutine
def up_telecom_gz(handler, partner):
    handler.up_req_time = time.localtime()
    tsp = str(int(time.time() * 1000))

    k = 'private:telecom_gz:{carrier}:{price}'.format(carrier=handler.carrier, price=handler.price)
    flowType = handler.slave.get(k)

    if flowType is None:
        handler.up_result = 5003
        return handler.up_result

    account = partner["account"]
    password = partner["password"]

    ran_num = random.randint(10001, 100001)
    hashCode = str(tsp) + str(ran_num)
    password = to_md5(to_md5(password) + hashCode)

    userPhone = partner["userPhone"]
    productCode = partner["productCode"]
    smsId = partner["smsId"]
    activityName = partner["activityName"]

    body = r'''<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:zz="http://zz.protocol.intf.tisson.cn">
   <soapenv:Header/>
   <soapenv:Body>
      <zz:odrerFlowRequest>
         <accountAuth>
            <account>{account}</account>
            <password>{password}</password>
            <hashCode>{hashCode}</hashCode>
         </accountAuth>
         <userPhone>{userPhone}</userPhone>
         <productCode>{productCode}</productCode>
         <flowType>{flowType}</flowType>
         <smsId>{smsId}</smsId>
         <activityName>{activityName}</activityName>
         <param1></param1>
         <param2></param2>
      </zz:odrerFlowRequest>
   </soapenv:Body>
</soapenv:Envelope>'''.format(account=account,
                              password=password,
                              hashCode=hashCode,
                              userPhone=userPhone,
                              productCode=productCode,
                              flowType=flowType,
                              smsId=smsId,
                              activityName=activityName,
                              )

    url = partner['url.order']

    h = {'Content-Type': 'text/xml;charset=UTF-8', 'SOAPAction': '""'}

    result = 9999
    up_result = None
    http_client = AsyncHTTPClient()

    try:
        request_log.info("PEOPLE REQ %s", body, extra={'orderid': handler.order_id})

        response = yield http_client.fetch(url, method='POST', body=body, headers=h, request_timeout=120)

    except HTTPError as http_error:
        request_log.error('PEOPLE CALL UPSTREAM FAIL %s', http_error, extra={'orderid': handler.order_id})
        result = 60000 + http_error.code
        response = None

    except Exception as e:
        request_log.error('PEOPLE CALL UPSTREAM FAIL %s', e, extra={'orderid': handler.order_id})
        response = None
    finally:
        http_client.close()

    handler.up_resp_time = time.localtime()

    if response and response.code == 200:
        response_body = response.body.decode()
        request_log.info("RESP %s", response_body, extra={'orderid': handler.order_id})
        try:
            sessionId = None
            root = ET.fromstring(response_body)
            if 'sessionId' in response_body:
                sessionId = root.find('.//sessionId').text

            if 'resultCode' in response_body:
                up_result = root.find('.//resultCode').text
                print(type(up_result))

            result = RESULT_MAP.get(up_result, 9)
            handler.up_result = str(up_result)
            handler.up_order_id = sessionId

            if handler.up_result == '0':
                handler.master.set("map:telecom_gz:{sessionId}".format(sessionId=sessionId), handler.order_id)

        except Exception as e:
            result = 9999
            handler.up_result = result
            request_log.error('PARSE UPSTREAM %s', e, extra={'orderid': handler.order_id})

    return result
