from flask import request, current_app, jsonify, session, g

from ihome import db
from ihome.models import User
from ihome.modules.api import api_blu
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
    pass


# 修改用户名
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
    pass

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
    pass


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
    pass

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
    pass
