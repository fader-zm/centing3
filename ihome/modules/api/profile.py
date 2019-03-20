import re

from flask import request, current_app, jsonify, session, g
from sqlalchemy.sql.functions import user

from ihome import db
from ihome.models import User
from ihome.modules.api import api_blu
from ihome.utils import constants
from ihome.utils.common import login_required
from ihome.utils.constants import QINIU_DOMIN_PREFIX
from ihome.utils.image_storage import storage_image
from ihome.utils.response_code import RET


# 获取用户信息
@api_blu.route('/user')
@login_required
def get_user_info():
    """
    获取用户信息
    1. 获取到当前登录的用户模型
    2. 返回模型中指定内容
    :return:
    """
    user_id = g.user_id
    user = User.query.get(user_id)

    return jsonify(errno=RET.OK, errmsg="OK", data=user.to_dict())


# 修改用户名avatar
@api_blu.route('/user/name', methods=["POST"])
@login_required
def set_user_name():
    """
    0. 判断用户是否登录
    1. 获取到传入参数
    2. 将用户名信息更新到当前用户的模型中
    3. 返回结果
    :return:
    """

    param_dict = request.json
    name = param_dict.get('name')
    if not name:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户名不能为空")
    user_id = g.user_id
    try:
        user = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询用户异常")

    user.name = name

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="用户名保存异常")
    return jsonify(errno=RET.OK, errmsg="修改用户名成功")


# 上传个人头像
@api_blu.route('/user/avatar', methods=['POST'])
@login_required
def set_user_avatar():
    """
    0. 判断用户是否登录
    1. 获取到上传的文件
    2. 再将文件上传到七牛云
    3. 将头像信息更新到当前用户的模型中
    4. 返回上传的结果<avatar_url>
    :return:
    """

    avatar = request.files.get('avatar')
    avatar = avatar.read()

    if not avatar:
        return jsonify(errno=RET.NODATA, errmsg="图片数据为空")

    try:
        avatar = storage_image(avatar)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg="七牛云上传图片异常")
    # 获取当前对象
    user_id = g.user_id
    # 根据对象id获取他的url
    try:
        user = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询用户异常")

    user.avatar_url = avatar

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存头像异常")
    full_url = constants.QINIU_DOMIN_PREFIX + avatar
    data = {
        "avatar_url": full_url
    }
    return jsonify(errno=RET.OK, errmsg="上传图片数据到七牛云成功", data=data)


# 获取用户实名信息
@api_blu.route('/user/auth')
@login_required
def get_user_auth():
    """
    1. 取到当前登录用户id
    2. 通过id查找到当前用户
    3. 获取当前用户的认证信息
    4. 返回信息
    :return:
    """
    # 取到当前登录用户id
    user_id = g.user_id

    # 通过id查找到当前用户
    try:
        user = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg='异常')

    # 获取当前用户的信息并转换成字典

    real_name = user.real_name
    id_card = user.id_card

    data = {
        'real_name': real_name,
        'id_card': id_card
    }
    # 返回信息
    return jsonify(errno=RET.OK, errmsg='OK', data=data)


# 设置用户实名信息
@api_blu.route('/user/auth', methods=["POST"])
@login_required
def set_user_auth():
    """
    1. 取到当前登录用户id
    2. 取到传过来的认证的信息
    3. 通过id查找到当前用户
    4. 更新用户的认证信息
    5. 保存到数据库
    6. 返回结果
    :return:
    """

    # 取到当前登录用户id
    user_id = g.user_id
    # 取到传过来的认证的信息
    real_name = request.json.get('real_name')
    id_card = request.json.get('id_card')

    # 判断身份证号码格式
    if not re.match('(^\d{15}$)|(^\d{18}$)|(^\d{17}(\d|X|x)$)', id_card):
        return jsonify(errno=RET.DATAERR, errmsg='身份证号码格式有误')

    # 通过id查找到当前用户
    try:
        user = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='查询用户对象异常')

    if not user:
        return jsonify(errno=RET.NODATA, errmsg='用户未登录')

    # 更新用户的认证信息
    user.real_name = real_name
    user.id_card = id_card

    # 保存到数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg='存储用户真实信息异常')

    # 返回结果
    return jsonify(errno=RET.OK, errmsg='设置用户实名信息成功', data=user.to_dict())
