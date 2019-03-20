import datetime
from _operator import or_

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
from sqlalchemy import not_


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
    return


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


# 首页房屋推荐展示
# /api/v1.0/houses/index
@api_blu.route('/houses/index')
def house_index():
    """
    首页房屋推荐展示
    :return:
    """
    # 首页展示最多的房屋数量
    # constants.HOME_PAGE_MAX_HOUSES
    # 查询房屋对象列表
    # 1. 筛选order.end_date > today 的房间, 筛选出已经预约或入住的房间
    orders = Order.query.filter(Order.end_date > datetime.date.today()).all()
    # 获取已被预约或入住的房间列表
    ordered_house_id = []
    if orders:
        ordered_house_id = [order.house_id for order in orders]
    
    # 去除已经预约或入住的房间, 找到可出租的房间, 以订单量, 房间信息更新时间为排序条件
    try:
        house_obj_list = House.query.filter(not_(House.id.in_(ordered_house_id)))\
            .order_by(House.order_count.desc(), House.update_time.desc())\
            .limit(constants.HOME_PAGE_MAX_HOUSES)
    except Exception as e:
        # current_app.logger.error('房间信息获取失败', e)
        return jsonify(errno=RET.DBERR, errmsg="房间信息获取失败")
    
    house_list = []
    # 查询每个房屋对象的房屋图片
    for house in house_obj_list if house_obj_list else None:
        house_list.append(house.to_basic_dict())
    return jsonify(errno=RET.OK, errmsg="OK", data=house_list)


# 搜索房屋/获取房屋列表
# /api/v1.0/houses
@api_blu.route('/houses')
@login_required
def get_house_list():
    """搜索房屋/获取房屋列表"""
    # 1. aid: 区域id, sd(start_day): 开始日期, ed(end_day): 结束时间,
    # sk(sort_key): 排序方式 booking(订单量), price­inc(低到高), price­des(高到低)
    # p(page): 页数，不传默认为1
    params = request.args
    today = datetime.date.today()
    aid = params.get("aid")
    sd = params.get("sd", today)
    ed = params.get("ed")
    page = 1
    # 每页显示的数据
    per_page = 10
    
    if len(params) == 0:
        print(len(params))
        try:
            # 没有任何查询条件时,快速的返回响应,提升用户体验
            houses_obj = House.query.filter().order_by(House.price.asc()).paginate(page, per_page, False)
        except Exception as e:
            return jsonify(errno=RET.DBERR, errmsg="数据库查询错误")
        
        # 房屋对象列表
        houses_obj_list = houses_obj.items
        # 总页数
        total_page = houses_obj.pages
        if houses_obj_list:
            data = dict(houses=[house.to_basic_dict() for house in houses_obj_list], total_page=total_page)
            return jsonify(errno=0, errmsg="ok", data=data)
    
    # 筛选条件列表
    # 请求地址条件
    house_filter_list = list()
    house_sort_list = list()
    # 已预约的房间, 筛选条件
    order_filter_list = list()
    # 请求页数
    if "p" in params.keys():
        page = params.get("p")
    
    # 地点
    if "aid" in params.keys():
        house_filter_list.append(House.area_id == params.get('cid'))
    
    # 排序方式
    if "sk" in params.keys():
        sk_rule = params.get("sk")
        if sk_rule == "booking":
            house_sort_list.append(House.order_count.desc())
        elif sk_rule == "price-inc":
            house_sort_list.append(House.price)
        elif sk_rule == "price-des":
            house_sort_list.append(House.price.desc())
    
    # 预订时间
    if "sd" in params.key():
        # 不能预订的房间
        start_date_str = params.get("sd")
        order_filter_list.append(Order.end_date > datetime.strptime(start_date_str, '%Y-%m-%d').date())
    if "ed" in params.key():
        # 不能预订的房间
        end_date_str = params.get("ed")
        order_filter_list.append(Order.begin_date < datetime.strptime(end_date_str, '%Y-%m-%d').date())
    
    # 不能预订的房间id
    nagtive_house_id_list = list()
    if len(order_filter_list) > 0:
        try:
            # 查询出不能预订的房间对象
            orders = Order.query.filter(or_(*order_filter_list)).all()
        except Exception as e:
            return jsonify(errno=RET.DBERR, errmsg="数据库查询错误")
        if orders:
            nagtive_house_id_list = [order.house_id for order in orders]
    
    # not_(House.id.in_(nagtive_house_id_list)) 为筛选条件, 筛选出可以预订的房间
    house_filter_list.append(not_(House.id.in_(nagtive_house_id_list)))
    
    # 查询出可以预约的房间
    try:
        houses_obj = House.query.filter(*house_filter_list).order_by(*house_sort_list).paginate(page, per_page, False)
    except Exception as e:
        return jsonify(errno=RET.DBERR, errmsg="数据库查询错误")
    
    # 房屋对象列表
    houses_obj_list = houses_obj.items
    # 总页数
    total_page = houses_obj.pages
    data = dict()
    if houses_obj_list:
        data = dict(houses=[house.to_basic_dict() for house in houses_obj_list], total_page=total_page)
        return jsonify(errno=0, errmsg="ok", data=data)
    return jsonify(errno=0, errmsg="ok", data=data)










