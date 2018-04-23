import json
import tornado
import logging
import time
from datetime import datetime, timedelta
from urllib.parse import quote
from tornado.httpclient import AsyncHTTPClient, HTTPError

from test.RSA_code import to_para
from utils.encryption_decryption import to_md5



request_log = logging.getLogger("madeira.request")

RESULT_MAP = {
    '0000000': 1,  # 成功
    'S999001': 9,  # 获取用户真实号码错误
    'S999002': 9,  # 请求参数中接口版本号不合法
    'S999003': 9,  # 校验请求IP地址不合法
    'S999004': 9,  # 请求参数中签名不合法
    'S999005': 9,  # 请求参数中订单不存在
    'S999006': 9,  # 请求参数中有不合法值
    'E100006': 9,  # 无优惠信息
    'E130223': 9,  # 取付费账户标志出错
    'E130298': 9,  # 取员工区域标识失败
    'E200001': 9,  # 工号[xxxx]没有操作[xxxx]的权限
    'E230113': 9,  # 重复缴费
    'E700001': 9,  # invalidRoute
    'E990000': 9,  # 获取用户真实号码错误
}

@tornado.gen.coroutine
def up_cmcc_sx(handler, partner):
    handler.up_req_time = time.localtime()

    appKey = partner["appKey"]
    timeStamp = (datetime.now() + timedelta(seconds=0)).strftime("%Y%m%d%H%M%S")
    login_no = partner["login_no"]
    acc_nbr = partner["acc_nbr"]
    group_id = partner["group_id"]
    member_role_id = partner["member_role_id"]
    gprs_accept = group_id + timeStamp + "000001"

    prod_prcid = None
    k = 'private:cmcc_sx:{carrier}:{price}'.format(carrier=handler.carrier, price=handler.price)
    prod_prcid = handler.slave.get(k)

    if prod_prcid is None:
        handler.up_result = 5003
        return handler.up_result

    data = ('acc_nbr={acc_nbr}&'
            'appKey={appKey}&'
            'gprs_accept={gprs_accept}&'
            'group_id={group_id}&'
            'login_no={login_no}&'
            'member_role_id={member_role_id}&'
            'prod_prcid={prod_prcid}&'
            'timeStamp={timeStamp}').format(
            appKey=appKey,
            timeStamp=timeStamp,
            login_no=login_no,
            acc_nbr=acc_nbr,
            prod_prcid=prod_prcid,
            group_id=group_id,
            member_role_id=member_role_id,
            gprs_accept=gprs_accept)

    sign = to_md5(quote(data))
    rsa_sign = to_para(sign)
    body = '&'.join([
        "acc_nbr=%s" % quote(acc_nbr),
        "appKey=%s" % quote(appKey),
        "gprs_accept=%s" % quote(gprs_accept),
        "group_id=%s" % quote(group_id),
        "login_no=%s" % quote(login_no),
        "member_role_id=%s" % quote(member_role_id),
        "prod_prcid=%s" % quote(prod_prcid),
        "timeStamp=%s" % quote(timeStamp),
        "sign=%s" % quote(rsa_sign),
    ])

    url = partner['url_auth']
    url = url + '?' + body

    h = {'Content-Type': 'application/json; charset=utf-8'}
    result = 9999
    up_result = None
    http_client = AsyncHTTPClient()
    try:
        request_log.info("REQU %s", body, extra={'orderid': handler.order_id})
        response = yield http_client.fetch(url, method='GET', headers=h, request_timeout=120)

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
        response_body = response.body.decode('utf8')
        request_log.info("RESP %s", response_body, extra={'orderid': handler.order_id})
        try:
            response_body = json.loads(response_body)
            up_result = response_body.get("resCode")
            sp_order_id = response_body.get("orderId")
            handler.up_order_id = sp_order_id

            result = RESULT_MAP.get(up_result, 9)
            if result == 1:
                handler.back_result = result
                yield handler.callback('1')
            elif result == 9:
                pass
            handler.up_result = up_result

            if handler.up_result == '0000000':
                handler.master.set("map:cmcc_sx:{sp_order_id}".format(sp_order_id=sp_order_id), handler.order_id)

        except Exception as e:
            result = 9999
            handler.up_result = result
            request_log.error('PARSE UPSTREAM %s', e, extra={'orderid': handler.order_id})
    return result

