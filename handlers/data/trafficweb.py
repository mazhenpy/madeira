# 乐流接口
import json
import logging
import time
from urllib.parse import urlencode

import tornado.gen
from tornado.httpclient import AsyncHTTPClient, HTTPError

from utils.encryption_decryption import to_md5

request_log = logging.getLogger("madeira.request")

RESULT_MAP = {
    "00000": 0,  # 成功
    "99999": 9,  # 失败
}


@tornado.gen.coroutine
def up_trafficweb(handler, partner):
    handler.up_req_time = time.localtime()

    user = partner["user"]
    password = partner["password"]
    request_no = handler.order_id
    mobile = handler.mobile

    prodtype = None
    k = 'private:trafficweb:{carrier}:{price}'.format(carrier=handler.carrier, price=handler.price)
    prodtype = handler.slave.get(k)

    if prodtype is None:
        handler.up_result = 5003
        return handler.up_result

    password = to_md5(password)
    data = mobile + prodtype + request_no + user + password
    sign = to_md5(data)

    body = {
        "request_no": request_no,
        "user": user,
        "prodtype": prodtype,
        "mobile": mobile,
        "sign": sign,
    }

    body = urlencode(body)

    url = partner["url_busi"]

    url = url + "?" + body
    result = 9999
    up_result = None
    http_client = AsyncHTTPClient()
    try:
        request_log.info("TRAFFICWEB REQU %s", body, extra={'orderid': handler.order_id})
        response = yield http_client.fetch(url, method='GET', request_timeout=120)

    except HTTPError as http_error:
        request_log.error('CALL UPSTREAM FAIL %s', http_error, extra={'orderid': handler.order_id})
        result = 60000 + http_error.code
        response = None

    except Exception as e:
        request_log.error('CALL UPSTREAM FAIL %s', e, extra={'orderid': handler.order_id})
        response = None
    finally:
        http_client.close()

    handler.up_resp_time = time.localtime()

    if response and response.code == 200:
        response_body = response.body.decode()
        request_log.info("TRAFFICWEB RESP {%s}", response_body.strip(), extra={'orderid': handler.order_id})
        try:
            response_body = json.loads(response_body)
            up_result = response_body.get("result_code")

            result = RESULT_MAP.get(up_result, 9)
            handler.up_result = up_result

        except Exception as e:
            result = 9999
            handler.up_result = result
            request_log.error('PARSE UPSTREAM %s', e, extra={'orderid': handler.order_id})
    return result
