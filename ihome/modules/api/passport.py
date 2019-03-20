# 实现图片验证码和短信验证码的逻辑
import re, random
from flask import request, abort, current_app, jsonify, make_response, json, session, g
from ihome.utils.common import login_required
from ihome import sr, db
from ihome.libs.captcha.pic_captcha import captcha
from ihome.libs.yuntongxun.sms import CCP
from ihome.models import User
from ihome.modules.api import api_blu
from ihome.utils import constants
from ihome.utils.response_code import RET


# 获取图片验证码  url:"/api/v1.0/imagecode?cur=
@api_blu.route("/imagecode")
def get_image_code():
    """
    1. 获取传入的验证码编号，并编号是否有值
    2. 生成图片验证码
    3. 保存编号和其对应的图片验证码内容到redis
    4. 返回验证码图片
    """
    # 1.获取传入的验证码编号，并编号是否有值
    cur = request.args.get("cur")
    if not cur:
        return abort(404)

    # 2.生成图片验证码  调用captcha.generate_captcha 返回一個元組　图片名称　验证码 图片数据
    image_name,real_image_code,image_data = captcha.generate_captcha()
    # 3.保存编号和其对应的图片验证码内容到redis 设置5分钟有效时长
    sr.setex(cur,constants.IMAGE_CODE_REDIS_EXPIRES, real_image_code)

    # 4.返回验证码图片  考虑兼容问题 再响应头设置返回数据的格式
    response = make_response(image_data)
    response.headers["Content_Type"]="image/png"
    return response


# 获取短信验证码 post请求 url:/api/v1.0/smscode
@api_blu.route('/smscode', methods=["POST"])
def send_sms():
    """
    1. 接收参数并判断是否有值
    2. 校验手机号是正确
    3. 通过传入的图片编码去redis中查询真实的图片验证码内容
    4. 进行验证码内容的比对
    5. 生成发送短信的内容并发送短信
    6. redis中保存短信验证码内容
    7. 返回发送成功的响应
    """
    #1. 接收参数(手机号码 用户填写的图片验证码 唯一编号)并判断是否有值
    mobile = request.json.get("mobile")
    image_code =request.json.get("image_code")
    image_code_id = request.json.get("image_code_id")

    if not all([mobile,image_code_id,image_code]):
        return jsonify(errno=RET.PARAMERR,errmsg="参数不足")

    # 2.判断手机号码格式是否正确
    if not re.match("1[3578][0-9]{9}",mobile):
        return jsonify(errno=RET.PARAMERR,errmsg="电话号码格式不对")

    # 3.通过传入的图片唯一编码去redis中查询真实的图片验证码内容
    try:
        real_image_code = sr.get(image_code_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg="redis数据库查询出错")

    # 4.把从redis取到的图片验证码和用户填写的验证码进行比对
    if real_image_code:
        sr.delete(image_code_id)
    else:
        return jsonify(errno=RET.NODATA,errmsg="图片验证码5分钟过期")

    if real_image_code.lower() != image_code.lower():
        return jsonify(errno=RET.DATAERR,errmsg="用户填写的图片验证码错误")

    # TODO:在获取短信验证码之前 判断该号码是否已经注册过了
    try:
        user = User.query.filter(User.mobile == mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg="数据库查询用户出错")
    if user:
        return jsonify(errno=RET.DATAEXIST,errmsg="用户已注册")

    # 5. 验证码正确 调用CPP对象的send_template_sms发送短信验证码 3个参数手机号码 [验证码,时效],模板
    #  生成6位数的验证码  不足6未0补齐
    real_phone_code = random.randint(1,999999)
    real_phone_code = "%06d" % real_phone_code
    #  发送成功返回0  失败-1
    try:
        result = CCP().send_template_sms(mobile,[real_phone_code,5],1)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR,errmsg="云通讯发送短信异常")
    if result == -1:
        return jsonify(errno=RET.THIRDERR,errmsg="云通讯发送短信异常")

    # 6. 验证码发送成功 redis中保存短信验证码内容 手机号码作为键
    sr.setex(mobile,constants.SMS_CODE_REDIS_EXPIRES,real_phone_code)
    # 7. 返回发送成功的响应
    return jsonify(errno=RET.OK,errmsg="发送短信验证码成功")


# 用户注册 url: /api/v1.0/user
@api_blu.route("/user", methods=["POST"])
def register():
    """
    1. 获取参数和判断是否有值
    2. 从redis中获取指定手机号对应的短信验证码的
    3. 校验验证码
    4. 初始化 user 模型，并设置数据并添加到数据库
    5. 保存当前用户的状态
    6. 返回注册的结果
    """

    # 1. 获取参数(mobile,phonecode,password)和判断是否有值
    mobile = request.json.get('mobile')
    phonecode = request.json.get('phonecode')
    password = request.json.get('password')

    if not all([mobile,phonecode,password]):
        return jsonify(errno=RET.PARAMERR,errmsg="参数不足")
    if not re.match("1[3578][0-9]{9}",mobile):
        return jsonify(errno=RET.PARAMERR,errmsg="电话号码格式不对")

    # 2. 从redis中获取指定手机号对应的短信验证码的
    try:
        real_phone_code = sr.get(mobile)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg="redis查询出错")

    if real_phone_code:
        sr.delete(mobile)
    else:
        return jsonify(errno=RET.NODATA,errmsg="短信验证码5分钟过期")

    # 3. 校验验证码
    if real_phone_code != phonecode:
        return jsonify(errno=RET.DATAERR,errmsg="短信验证码输入错误")

    # 4. 短信验证码正确 初始化 user 模型，并设置数据并添加到数据库
    user = User()
    user.mobile = mobile
    user.name = mobile
    user.password = password
    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR,errmsg="数据库保存用户数据出错")

    # 5. session保存当前用户的状态
    session["mobile"] = user.mobile
    session["name"] = user.name
    session["user_id"] = user.id
    # 6. 返回注册的结果
    return jsonify(errno=RET.OK,errmsg="注册成功")



# 用户登录
@api_blu.route("/session", methods=["POST"])
def login():
    """
    1. 获取参数和判断是否有值
    2. 从数据库查询出指定的用户
    3. 校验密码
    4. 保存用户登录状态
    5. 返回结果
    :return:
    """

    # 获取参数
    mobile = request.json.get('mobile')
    password = request.json.get('password')
    # print(mobile, password)

    # 判断是否有值
    if not all([mobile, password]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数不足')

    # 判断手机号码格式
    if not re.match(r'^1[3578]\d{9}', mobile):
        return jsonify(errno=RET.PARAMERR, errmsg='手机号码格式错误')

    # 从数据库中查询出指定用户
    try:
        user = User.query.filter(User.mobile == mobile).first()
        # print(user)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='查询用户对象异常')
    if not user:
        return jsonify(errno=RET.NODATA, errmsg='用户不存在')

    # 校验密码
    if user.check_passowrd(password) is False:
        return jsonify(errno=RET.DATAERR, errmsg='密码填写错误')

    # 保存用户登录状态
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.PARAMERR, errmsg='异常')
    session['mobile'] = user.mobile
    session['name'] = user.name
    session['user_id'] = user.id

    # 返回结果
    return jsonify(errno=RET.OK, errmsg='登录成功')


# 获取登录状态
@api_blu.route('/session')
@login_required
def check_login():
    """
    检测用户是否登录，如果登录，则返回用户的名和用户id
    :return:
    """
    user_id = g.user_id
    # 从数据库中查询出指定用户
    try:
        user = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='查询用户对象异常')

    # 将用户对象转换成字典
    user_dict = user.to_dict() if user else None
    data = {
        'name': user.name,
        'user_id': user_id
    }
    # 返回结果
    return jsonify(errno=RET.OK, errmsg='OK', data=data)


# 退出登录
@api_blu.route("/session", methods=["DELETE"])
def logout():
    """
    1. 清除session中的对应登录之后保存的信息
    :return:
    """
    session.pop('user_id')
    session.pop('mobile')
    session.pop('name')
    return jsonify(errno=RET.OK, errmsg='退出登录成功')

