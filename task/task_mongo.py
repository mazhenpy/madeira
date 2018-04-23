import logging
from sqlalchemy import Column, Integer, String, DateTime, Date
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pymongo

Base = declarative_base()


class Order(Base):
    __tablename__ = 'order_100001'

    id = Column(Integer, primary_key=True)
    order_id = Column(String)
    user_id = Column(String)
    price = Column(Integer)
    mobile = Column(String)
    sp_order_id = Column(String)
    req_time = Column(DateTime)
    resp_time = Column(DateTime)
    back_time = Column(DateTime)
    result = Column(String)
    back_result = Column(String)
    value = Column(Integer)
    balance = Column(Integer)  # new
    area = Column(String)  # new
    product = Column(String)  # new2
    scope = Column(String)


class UpOrder(Base):
    __tablename__ = 'up_order_100001'

    id = Column(Integer, primary_key=True)
    stage = Column(Integer)
    order_id = Column(String)
    up_order_id = Column(String)
    route = Column(String)
    price = Column(Integer)
    cost = Column(Integer)
    up_cost = Column(String)
    up_req_time = Column(DateTime)
    up_resp_time = Column(DateTime)
    up_back_time = Column(DateTime)
    up_result = Column(String)
    up_back_result = Column(String)


task_log = logging.getLogger("madeira.task")


class MongoTask():
    def __init__(self):
        engine = create_engine('mysql+mysqlconnector://truman:11111@192.168.1.154/madeira')

        self.session = sessionmaker(bind=engine)()

        conn = pymongo.Connection('192.168.1.154', 27017)
        self.db = conn['order_test']

    def task_order(self):
        order_query_list = self.session.query(Order).all()

        for order in order_query_list:
            self.db.Account.insert({
                "_id": order.order_id,
                "price": order.price,
                "mobile": order.mobile,
                "sp_order_id": order.sp_order_id,
                "req_time": order.req_time,
                "resp_time": order.resp_time,
                "result": order.result,
                "back_result": order.back_result,
                "value": order.value,
                "balance": order.balance,
                "area": order.area,
                "product": order.product,
                "scope": order.scope,
            })

        up_order_query_list = self.session.query(UpOrder).all()
        for up_order in up_order_query_list:
            self.db.Account.update(
                {"_id": up_order.order_id},
                {'$set': {
                    'stage': up_order.stage,
                    'up_order_id': up_order.up_order_id,
                    'route': up_order.route,
                    'price': up_order.price,
                    'cost': up_order.cost,
                    'up_cost': up_order.up_cost,
                    'up_resp_time': up_order.up_resp_time,
                    'up_back_time': up_order.up_back_time,
                    'up_result': up_order.up_result,
                    'up_back_result': up_order.up_back_result,
                }}, multi=True
            )


if __name__ == "__main__":
    a = MongoTask()
    a.task_order()