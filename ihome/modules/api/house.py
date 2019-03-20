import datetime

from flask import current_app, jsonify, request, g, session
from ihome import sr, db
from ihome.models import Area, House, Facility, HouseImage, Order
from ihome.modules.api import api_blu
from ihome.utils import constants
from ihome.utils.common import login_required
from ihome.utils.constants import AREA_INFO_REDIS_EXPIRES, QINIU_DOMIN_PREFIX, HOUSE_LIST_PAGE_CAPACITY, \
    HOME_PAGE_MAX_HOUSES, HOME_PAGE_DATA_REDIS_EXPIRES
from ihome.utils.image_storage import storage_image
from ihome.utils.response_code import RET


# 我的发布列表
@api_blu.route('/user/houses')
@login_required
def get_user_house_list():
    """
    获取用户房屋列表
    1. 获取当前登录用户id
    2. 查询数据
    :return:
    """
    pass


# 获取地区信息
@api_blu.route("/areas")
def get_areas():
    """
    1. 查询出所有的城区
    2. 返回
    :return:
    """
    try:
        areas = Area.query.all()
    except Exception as e:
        return jsonify(errno=RET.DBERR, errmsg="数据库错误")
    area_list = []
    for area in areas if areas else None:
        area_list.append(area.to_dict())

    return jsonify(errno=RET.OK, errmsg="ok", data=area_list)


# 上传房屋图片
@api_blu.route("/houses/<int:house_id>/images", methods=['POST'])
@login_required
def upload_house_image(house_id):
    """
    1. 取到上传的图片
    2. 进行七牛云上传
    3. 将上传返回的图片地址存储
    4. 进行返回
    :return:
    """
    pass


# 发布房源
@api_blu.route("/houses", methods=["POST"])
@login_required
def save_new_house():
    """
    1. 接收参数并且判空
    2. 将参数的数据保存到新创建house模型
    3. 保存house模型到数据库
    前端发送过来的json数据
    {
        "title":"",
        "price":"",
        "area_id":"1",
        "address":"",
        "room_count":"",
        "acreage":"",
        "unit":"",
        "capacity":"",
        "beds":"",
        "deposit":"",
        "min_days":"",
        "max_days":"",
        "facility":["7","8"]
    }
    :return:
    """
    #获得前端发送的数据
    datas = request.json
    title = datas.get("title")
    price = datas.get("price")
    area_id = datas.get("area_id")
    address = datas.get("address")
    room_count = datas.get("room_count")
    acreage = datas.get("acreage")
    unit = datas.get("unit")
    capacity = datas.get("capacity")
    beds = datas.get("beds")
    deposit = datas.get("deposit")
    min_days = datas.get("min_days")
    max_days = datas.get("max_days")
    facility = datas.get("facility")
    #非空和日期判断
    if not all([title, price, area_id, address, room_count, acreage, unit
                   , capacity, beds, deposit, min_days, max_days, facility]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")
    if int(min_days)< 0 or int(max_days)<0 or int(min_days)>int(max_days):
        return jsonify(errno=RET.PARAMERR,errmsg="参数错误")
    #将参数添加到数据库
    house = House()
    house.title = title
    house.price = price
    house.area_id = area_id
    house.address = address
    house.room_count = room_count
    house.acreage = acreage
    house.unit = unit
    house.capacity = capacity
    house.beds = beds
    house.deposit = deposit
    house.min_days = min_days
    house.max_days = max_days
    house.user_id = g.user_id
    house.facilities.extend([Facility.query.get(int(fid)) for fid in facility])
    try:
        db.session.add(house)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存房源对象错误")
    data = {"house_id": house.id}
    return jsonify(errno=RET.OK, errmsg="OK", data=data)


# 房屋详情/api/v1.0/houses/<int:house_id>
@api_blu.route('/houses/<int:house_id>')
def get_house_detail(house_id):
    """
    1. 通过房屋id查询出房屋模型
    :param house_id:
    :return:
    # """
    user_id=session.get("user_id")
    try:
        house=House.query.get(house_id)
    except Exception as e:
        return jsonify(errno=RET.DBERR,errmsg="查询数据库有误")
    house_dict=house.to_full_dict()

    data={
        "house":house_dict,
        "user_id":user_id
    }
    return jsonify(errno=RET.OK,errmsg="OK",data=data)


# 获取首页展示内容
@api_blu.route('/houses/index')
def house_index():
    """
    获取首页房屋列表
    :return:
    """
    pass


# 搜索房屋/获取房屋列表
@api_blu.route('/houses')
def get_house_list():
    pass
