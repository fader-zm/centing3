import datetime

from flask import current_app, jsonify, request, g, session
from ihome import sr, db
from ihome.models import Area, House, Facility, HouseImage, Order, User
from ihome.modules.api import api_blu
from ihome.utils import constants
from ihome.utils.common import login_required
from ihome.utils.constants import AREA_INFO_REDIS_EXPIRES, QINIU_DOMIN_PREFIX, HOUSE_LIST_PAGE_CAPACITY, \
    HOME_PAGE_MAX_HOUSES, HOME_PAGE_DATA_REDIS_EXPIRES
from ihome.utils.image_storage import storage_image
from ihome.utils.response_code import RET


# 我的发布列表
# /api/v1.0/user/houses
@api_blu.route('/user/houses')
@login_required
def get_user_house_list():
    """
    获取用户房屋列表
    1. 获取当前登录用户id
    2. 查询数据
    :return:
    """
    user_id = request.json.get("user_id")

    try:
        user = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="查询用户异常")
    # user = []
    if not user:
        return jsonify(reeno=RET.SESSIONERR, errmsg="用户未登录")

    # 获取房子数据
    house = []
    try:
        # house = House.query.filter(house_id)
        house_obj_list = House.query.filter(user_id == House.user_id)
    except Exception as error:
        return jsonify(errno=RET.PARAMERR, errmsg="查询房子数据异常")
    # 将房子对象转换成房子数据列表
    user_house_dict = None
    for house in house_obj_list if house_obj_list else None:
        user_house_dict.append(house.to_full_dict())


    data = user_house_dict

    # 获取房子图片
    area_name_list = None
    area_obj_list = Area.query.all()
    for area_name in area_obj_list if area_obj_list else None:
        area_name_list.append(area_name.to_dict())

    data = area_name_list




# 获取地区信息
@api_blu.route("/areas")
def get_areas():
    """
    1. 查询出所有的城区
    2. 返回
    :return:
    """
    try:
        area_name_all = Area.quary.all(Area.id)
    except Exception as error:
        return jsonify(errno=RET.DBERR, errmsg="查询城区数据异常")

    area_name_all_list = None
    for area_name in area_name_all if area_name_all else None:
        area_name_all_list.append(area_name.to_dict())

    data = area_name_all_list

    return data


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
    #https://shimo.im/docs/VDyhJJddhh8QgpQd/ 《七牛云接口》

    index_img_url = request.files.get("house_id")
    user_id = request.json.get("user_id")

    if not all([index_img_url, user_id]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")

    #上传图片到七牛云
    try:
        img_name = upload_house_image(index_img_url.read())
    except Exception as e:
        return jsonify(errno=RET.THIRDERR, errmsg="上传图片到七牛云异常")

    #提交数据到数据库
    try:
        db.session.add()
        db.session.commit()
    except Exception as error:
        db.session.roolback()
        return jsonify(errno=RET.SESSIONERR, errmsg="提交数据库异常")

    img_name_url = constants.QINIU_DOMIN_PREFIX + img_name

    return img_name_url





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
    pass


# 房屋详情
@api_blu.route('/houses/<int:house_id>')
def get_house_detail(house_id):
    """
    1. 通过房屋id查询出房屋模型
    :param house_id:
    :return:
    """
    pass


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
