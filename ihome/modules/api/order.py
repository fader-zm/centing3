import time
from datetime import datetime

from sqlalchemy import or_, not_, and_
from ihome import db, sr
from ihome.models import House, Order
from ihome.utils.common import login_required
from ihome.utils.response_code import RET
from . import api_blu
from flask import request, g, jsonify, current_app, session


# 预订房间
@api_blu.route('/orders', methods=['POST'])
@login_required
def add_order():
    user_id = g.user_id
    # 1. 获取参数

    start_date = request.json.get("start_date")
    end_date = request.json.get("end_date")
    house_id = request.json.get("house_id")
    house_id = int(house_id)
    # 2. 校验参数

    if not all([start_date, end_date, house_id]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")

    # 3. 查询指定房屋是否存在
    try:
        house = House.query.filter(House.id == house_id).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询house对象错误")
    if not house:
        return jsonify(errno=RET.DATAEXIST, errmsg="房屋不存在")
    # 4. 判断当前房屋的房主是否是登录用户
    if user_id == house.user_id:
        return jsonify(errno=RET.USERERR, errmsg="您是房东,不可以预订自己的房间")
    # 5. 查询当前预订时间是否存在冲突
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")
    days = (end_date - start_date).days
    if house.max_days == 0:
        if days < house.min_days:
            return jsonify(errno=RET.PARAMERR, errmsg="预定天数小于最小预订天数")
    else:
        if days > house.max_days:
            return jsonify(errno=RET.PARAMERR, errmsg="预定天数大于最大预订天数")

    # 如果订单状态是取消或者拒单,则该订单仍可进行下单
    try:
        date_count = Order.query.filter(or_(and_(start_date <= Order.begin_date, end_date >= Order.begin_date),
                                            and_(start_date <= Order.end_date, end_date >= Order.end_date),
                                            and_(start_date >= Order.begin_date, end_date <= Order.end_date),
                                            and_(start_date <= Order.begin_date, end_date >= Order.end_date))
                                        ).filter(not_(Order.status.in_(["CANCELED", "REJECTED"]))).count()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询参数错误")

    if date_count > 0:
        return jsonify(errno=RET.DATAEXIST, errmsg="该时间段已被预订")

    # 6. 生成订单模型，进行下单
    new_order = Order()
    new_order.user_id = user_id
    new_order.house_id = house_id
    new_order.begin_date = start_date
    new_order.end_date = end_date
    new_order.days = days
    new_order.house_price = house.price
    new_order.amount = house.price * days

    try:
        db.session.add(new_order)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存数据失败")

    data = {
        "order_id": new_order.id
    }
    # 7. 返回下单结果
    return jsonify(errno=RET.OK, errmsg="生成订单成功", data=data)


# 获取我的订单
@api_blu.route('/orders')
@login_required
def get_orders():
    """
    1. 去订单的表中查询当前登录用户下的订单
    2. 返回数据
    """
    user_id = g.user_id
    if not user_id:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")
    role = request.args.get("role")
    if role == "custom":
        try:
            order_list = Order.query.filter(Order.user_id == user_id).order_by(Order.create_time.desc())
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="查询订单对象错误")
        order_dict_list = []
        for order in order_list if order_list else []:
            order_dict_list.append(order.to_dict())
        data = {
            "orders": order_dict_list
        }
        return jsonify(errno=RET.OK, errmsg="查询订单信息成功", data=data)
    if role == "landlord":
        try:
            own_house_list = House.query.filter(House.user_id == user_id).all()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="查询房屋对象错误")
        own_house_id_list = [house.id for house in own_house_list]
        try:
            order_list = Order.query.filter(Order.house_id.in_(own_house_id_list)).order_by(Order.create_time.desc())
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="查询订单对象错误")
        order_dict_list = []
        for order in order_list if order_list else []:
            order_dict_list.append(order.to_dict())
        data = {
            "orders": order_dict_list
        }
        return jsonify(errno=RET.OK, errmsg="查询订单信息成功", data=data)


# 接受/拒绝订单
@api_blu.route('/orders', methods=["PUT"])
@login_required
def change_order_status():
    """
    1. 接受参数：order_id
    2. 通过order_id找到指定的订单，(条件：status="待接单")
    3. 修改订单状态
    4. 保存到数据库
    5. 返回
    :return:
    """
    user_id = g.user_id
    if not user_id:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")

    order_id = request.json.get("order_id")
    action = request.json.get("action")
    reason = request.json.get("reason")
    order_id = int(order_id)
    try:
        order = Order.query.filter(Order.id == order_id).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询订单对象错误")
    if order.status != "WAIT_ACCEPT":
        return jsonify(errno=RET.DATAERR, errmsg="订单不是待接单状态")
    if action == "accept":
        order.status = "WAIT_COMMENT"
        try:
            db.session.commit()
        except Exception as e:
            current_app.logger.error(e)
            db.session.rollback()
            return jsonify(errno=RET.DBERR, errmsg="保存数据库失败")
        return jsonify(errno=RET.OK, errmsg="接单成功")
    if action == "reject":
        order.status = "REJECTED"
        order.comment = reason
        try:
            db.session.commit()
        except Exception as e:
            current_app.logger.error(e)
            db.session.rollback()
            return jsonify(errno=RET.DBERR, errmsg="保存数据库失败")
        return jsonify(errno=RET.OK, errmsg="拒单成功")


# 评论订单
@api_blu.route('/orders/comment', methods=["PUT"])
@login_required
def order_comment():
    """
    订单评价
    1. 获取参数
    2. 校验参数
    3. 修改模型
    :return:
    """
    user_id = g.user_id
    comment = request.json.get('comment')
    order_id = request.json.get('order_id')

    if not all([comment, order_id]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数不足')

    try:
        order = Order.query.filter(order_id == Order.id, Order.user_id == user_id,
                                   Order.status == 'WAIT_COMMENT').first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='查询订单对象异常')

    if not order:
        return jsonify(errno=RET.NODATA, errmsg='无订单')

    order.comment = comment
    order.status = 'COMPLETE'

    try:
        db.session.add(order)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg='数据库存储订单异常')

    return jsonify(errno=RET.OK, errmsg='发表评论成功')
