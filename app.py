import numpy as np
import tensorflow as tf
import tensorflow_hub as hub
from tensorflow import keras
from flask_jwt_extended import JWTManager, create_access_token
import bcrypt
from pymongo import ReturnDocument
import re
import jwt
import json
from bson.objectid import ObjectId
from bson import json_util
from bson.json_util import dumps, loads
from functools import wraps
from flask_cors import CORS, cross_origin
from flask.helpers import url_for
from flask_pymongo import PyMongo
import datetime
from flask import Flask, request, Response, jsonify, session, redirect
app = Flask(__name__)
jwt = JWTManager(app)

CORS(app)


app.config["MONGO_URI"] = "mongodb+srv://hunnurjirao:*************@cluster0.ubnum.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"
mongo = PyMongo(app)

app.secret_key = 'super secret key'
app.config["JWT_SECRET_KEY"] = "this-is-secret-key"


# user api


# @app.route("/predict")
# def pred():
#     p = model.predict([10.0])
#     print(p)
#     return jsonify(message='done')

# @app.route("/getAllUsers", methods=['GET'])
# def getAllUsers():
#     allUsers = mongo.db.users
#     user = dumps(
#         list(allUsers.find({})), indent=2)

#     user = json.loads(user)
#     return jsonify(user), 201

@app.route('/testpage')
def testpage():
    return jsonify(message='all good!')


@app.route("/userRegister", methods=['POST', 'GET'])
def userRegister():
    if request.method == 'POST':
        allUsers = mongo.db.users
        user = allUsers.find_one({'email': request.json['email']})
        username = allUsers.find_one({'username': request.json['username']})
        phone = allUsers.find_one({'phone': request.json['phone']})

        if user:
            return jsonify(message='Email already exists'), 401
        if username:
            return jsonify(message='Username already exists'), 401
        if phone:
            return jsonify(message='Phone Number already exists'), 401

        if request.json['password'] != request.json['cpassword']:
            return jsonify(message='Password Not Matching!'), 401

        hashpw = bcrypt.hashpw(
            request.json['password'].encode('utf-8'), bcrypt.gensalt())

        hashCpw = bcrypt.hashpw(
            request.json['cpassword'].encode('utf-8'), bcrypt.gensalt())

        access_token = create_access_token(identity=request.json['email'])

        allUsers.insert({
            'email': request.json['email'],
            'password': hashpw,
            'cpassword': hashCpw,
            "username": request.json['username'],
            "phone": request.json['phone'],
            'tokens': [
                {
                    'token': str(access_token)
                }
            ]
        })

        session['email'] = request.json['email']
        return jsonify(token=str(access_token)), 201


@app.route("/userLogin", methods=['POST'])
def userLogin():
    allUsers = mongo.db.users
    user = allUsers.find_one({'email': request.json['email']})

    if user:
        if bcrypt.hashpw(request.json['password'].encode('utf-8'), user['password']) == user['password']:
            # session['email'] = request.json['email']
            access_token = create_access_token(identity=request.json['email'])
            user['tokens'].append({'token': str(access_token)})
            allUsers.save(user)
            return jsonify(token=str(access_token)), 201
    return jsonify(message='Invalid Username/Password'), 401


@app.route("/getUserData", methods=['POST'])
def getUserData():

    allUsers = mongo.db.users
    # user = allUsers.find_one({'tokens.token': request.json['auth']})
    user = dumps(
        list(allUsers.find({'tokens.token': request.json['auth']})), indent=2)

    if user:
        user = json.loads(user)
        return jsonify(user), 201

    return jsonify(message='Something went wrong'), 401


@app.route("/addtoCart", methods=['PUT'])
def addtoCart():

    newCartProd = {

        'pid': request.json['pid'],
        'productUrl': request.json['productUrl'],
        'productName': request.json['productName'],
        'productPrice': request.json['productPrice'],
        'productType': request.json['productType'],
    }
    uid = request.json['uid']

    allUsers = mongo.db.users
    user = list(allUsers.find(
        {'_id': ObjectId(uid), 'cartProducts':  {'$elemMatch': newCartProd}}))

    if len(user) > 0:
        return jsonify(message='Product Already Added!'), 401

    allUsers.find_one_and_update({'_id': ObjectId(uid)},
                                 {'$push': {"cartProducts":
                                            {
                                                '_id': ObjectId(),
                                                'pid': request.json['pid'],
                                                'productUrl': request.json['productUrl'],
                                                'productName': request.json['productName'],
                                                'productPrice': request.json['productPrice'],
                                                'productType': request.json['productType'],
                                            }
                                            }},
                                 return_document=ReturnDocument.AFTER)
    return jsonify(message='Product Added Successfully!'), 201


@app.route("/removefromCart", methods=['PUT'])
def removefromCart():
    allUsers = mongo.db.users
    uid = request.json['uid']
    cid = request.json['cid']

    try:
        allUsers.find_one_and_update({'_id': ObjectId(uid)},
                                     {'$pull': {
                                         "cartProducts": {'_id': ObjectId(cid)}
                                     }},
                                     return_document=ReturnDocument.AFTER
                                     )
        return jsonify(message='Product Removed Successfully!'), 201

    except Exception as e:
        print(e)
        return jsonify(message='Something went wrong!'), 401


@app.route("/deleteOrder", methods=['PUT'])
def deleteOrder():
    allUsers = mongo.db.users
    uid = request.json['uid']
    oid = request.json['oid']
    pid = request.json['pid']
    qty = request.json['qty']

    verifyOrder = {
        'pid': ObjectId(pid),
        'uid': ObjectId(uid),
        'Quantity': qty
    }
    try:

        allProducts = mongo.db.products
        prod = allProducts.find_one({'_id': ObjectId(pid)})

        if prod:
            aid = prod['adminId']

            allAdmins = mongo.db.admins
            admin = allAdmins.find_one({'_id': ObjectId(aid)})

            # admin = list(allAdmins.find(
            #     {'_id': ObjectId(aid), 'orders':  {'$elemMatch': verifyOrder}}))

            admin = admin.get('orders')

            # print('admin==>'+str(admin))
            # print(type(admin))

            for ord in admin:
                if ord.get('pid') == pid and ord.get('uid') == uid and ord.get('Quantity') == qty:
                    aoid = ord.get('_id')

        else:

            return jsonify(message='Something went wrong!'), 401

        allUsers.find_one_and_update({'_id': ObjectId(uid)},
                                     {'$pull': {
                                         "orders": {'_id': ObjectId(oid)}
                                     }},
                                     return_document=ReturnDocument.AFTER
                                     )

        allAdmins.find_one_and_update({'_id': ObjectId(aid)},
                                      {'$pull': {
                                          "orders": {'_id': ObjectId(aoid)}
                                      }},
                                      return_document=ReturnDocument.AFTER
                                      )
        return jsonify(message='Order Cancelled Successfully!'), 201

    except Exception as e:
        print(e)
        return jsonify(message='Something went wrong!'), 401


@app.route("/userOrders", methods=['PUT'])
def userOrders():
    newOrder = {
        'pid': request.json['pid'],
        'productUrl': request.json['productUrl'],
        'productName': request.json['productName'],
        'productPrice': request.json['productPrice'],
        'productType': request.json['productType'],
        'Quantity': request.json['qty']
    }
    uid = request.json['uid']
    pid = request.json['pid']

    allUsers = mongo.db.users
    user = list(allUsers.find(
        {'_id': ObjectId(uid), 'orders':  {'$elemMatch': newOrder}}))

    if len(user) > 0:
        return jsonify(message='Order already Placed'), 401
    allProducts = mongo.db.products
    prod = allProducts.find_one({'_id': ObjectId(pid)})

    if prod:
        aid = prod['adminId']

        allAdmins = mongo.db.admins
        admin = allAdmins.find_one({'_id': ObjectId(aid)})
        if admin:
            allAdmins.find_one_and_update({'_id': ObjectId(aid)},
                                          {'$push': {"orders":
                                                     {
                                                         '_id': ObjectId(),
                                                         'pid': request.json['pid'],
                                                         'uid': request.json['uid'],
                                                         'productUrl': request.json['productUrl'],
                                                         'productName': request.json['productName'],
                                                         'productPrice': request.json['productPrice'],
                                                         'productType': request.json['productType'],
                                                         'Quantity': request.json['qty']
                                                     }
                                                     }},
                                          return_document=ReturnDocument.AFTER)
    else:
        return jsonify(message='Something went wrong!')

    allUsers.find_one_and_update({'_id': ObjectId(uid)},
                                 {'$push': {"orders":
                                            {
                                                '_id': ObjectId(),
                                                'pid': request.json['pid'],
                                                'productUrl': request.json['productUrl'],
                                                'productName': request.json['productName'],
                                                'productPrice': request.json['productPrice'],
                                                'productType': request.json['productType'],
                                                'Quantity': request.json['qty']
                                            }
                                            }},
                                 return_document=ReturnDocument.AFTER)
    return jsonify(message='Order Placed Successfully!'), 201


@app.route("/suggestions", methods=['PUT'])
def suggestions():
    return 401


@app.route("/logoutUser", methods=['POST'])
def logoutUser():
    allUsers = mongo.db.users
    user = allUsers.find_one({'tokens.token': request.json['auth']})

    if user:
        user['tokens'] = []
        allUsers.save(user)
        return jsonify(message='Logout Successfully!'), 201
    return jsonify(message='Something went wrong!'), 401

# all products


@app.route("/getAllProducts", methods=['GET'])
def getAllProducts():
    allProducts = mongo.db.products
    prod = dumps(
        list(allProducts.find({})), indent=2)

    prod = json.loads(prod)
    return jsonify(prod), 201


@app.route("/addComments", methods=['POST'])
def addComments():
    comment = request.json['comment']
    uid = request.json['uid']
    pid = request.json['pid']
    date = datetime.datetime.now()
    try:
        model = keras.models.load_model('sentimentAnalysis.h5', custom_objects={
                                        'KerasLayer': hub.KerasLayer})

        pred = model.predict([comment])[0][0]

        if (pred >= 0.5):
            sentiment = 1
        else:
            sentiment = 0

        allProducts = mongo.db.products

        allUsers = mongo.db.users
        user = allUsers.find_one({'_id': ObjectId(uid)})
        username = user['username']

        allProducts.find_one_and_update({'_id': ObjectId(pid)},
                                        {'$push': {"comments":
                                                   {
                                                       '_id': ObjectId(),
                                                       'uid': uid,
                                                       'username': username,
                                                       'comment': comment,
                                                       'sentiment': sentiment,
                                                       'date': str(date)
                                                   }
                                                   }},
                                        return_document=ReturnDocument.AFTER)
        return jsonify(message='Thanks for your Feedback!'), 201

    except Exception as e:
        print(e)
        return jsonify(message='Something went Wrong!'), 401


@app.route("/addRating", methods=['POST'])
def addRating():
    rating = request.json['rating']
    pid = request.json['pid']
    allProducts = mongo.db.products

    prod = allProducts.find_one({'_id': ObjectId(pid)})

    try:
        prev_rating = prod['rating']

        new_rating = round((prev_rating + rating)/2, 1)

        prod['rating'] = new_rating
        allProducts.save(prod)

    except:
        allProducts.update({"_id": ObjectId(pid)},
                           {"$set": {"rating": rating}})

    return jsonify(message='Thanks for Rating!'), 201


# admin api


@app.route("/adminRegister", methods=['POST', 'GET'])
def adminRegister():
    if request.method == 'POST':
        allUsers = mongo.db.admins
        user = allUsers.find_one({'email': request.json['email']})
        companyName = allUsers.find_one(
            {'companyName': request.json['companyName']})
        phone = allUsers.find_one({'phone': request.json['phone']})

        if user:
            return jsonify(message='Email already exists'), 401
        if companyName:
            return jsonify(message='companyName already exists'), 401
        if phone:
            return jsonify(message='Phone Number already exists'), 401

        if request.json['password'] != request.json['cpassword']:
            return jsonify(message='Password Not Matching!'), 401

        hashpw = bcrypt.hashpw(
            request.json['password'].encode('utf-8'), bcrypt.gensalt())

        hashCpw = bcrypt.hashpw(
            request.json['cpassword'].encode('utf-8'), bcrypt.gensalt())

        access_token = create_access_token(identity=request.json['email'])

        allUsers.insert({
            'email': request.json['email'],
            "companyName": request.json['companyName'],
            "phone": request.json['phone'],
            'password': hashpw,
            'cpassword': hashCpw,
            'tokens': [
                {
                    'token': str(access_token)
                }
            ]
        })

        return jsonify(token=str(access_token)), 201


@app.route("/adminLogin", methods=['POST'])
def adminLogin():
    allUsers = mongo.db.admins
    user = allUsers.find_one({'email': request.json['email']})

    if user:
        if bcrypt.hashpw(request.json['password'].encode('utf-8'), user['password']) == user['password']:
            # session['email'] = request.json['email']
            access_token = create_access_token(identity=request.json['email'])
            user['tokens'].append({'token': str(access_token)})
            allUsers.save(user)
            return jsonify(token=str(access_token)), 201
    return jsonify(message='Invalid Username/Password'), 401


@app.route("/getAdminData", methods=['POST'])
def getAdminData():

    allUsers = mongo.db.admins
    # user = allUsers.find_one({'tokens.token': request.json['auth']})
    user = dumps(
        list(allUsers.find({'tokens.token': request.json['auth']})), indent=2)

    if user:
        user = json.loads(user)
        return jsonify(user), 201

    return jsonify(message='Something went wrong'), 401


@app.route("/addProduct", methods=['POSt'])
def addProduct():
    adminName = request.json['adminName']
    adminId = request.json['adminId']
    productName = request.json['productName']
    productPrice = request.json['productPrice']
    productUrl = request.json['productUrl']
    productCategory = request.json['productCategory']

    allProducts = mongo.db.products
    prod = allProducts.find_one({'productName': productName,
                                 'productPrice': productPrice,
                                 'adminId': adminId,
                                 })

    if prod:
        return jsonify(message='Product Already Added'), 401
    allProducts.insert({
        'adminId': adminId,
        'adminName': adminName,
        'productUrl': productUrl,
        'productName': productName,
        'productPrice': productPrice,
        'productCategory': productCategory

    })
    return jsonify(message='Product Added Successfully'), 201


@app.route("/editProduct", methods=['PUT'])
def editProduct():
    id = request.json['uid']
    productName = request.json['productName']
    productPrice = request.json['productPrice']
    productUrl = request.json['productUrl']

    allProducts = mongo.db.products
    prod = allProducts.find_one({'_id': ObjectId(id)})

    if prod:
        prod['productName'] = productName
        prod['productPrice'] = productPrice
        prod['productUrl'] = productUrl
        allProducts.save(prod)
        return jsonify(message='Product Updated Successfully'), 201
    return jsonify(message='Something went wrong'), 401


@app.route("/deleteProduct", methods=['PUT'])
def deleteProduct():

    id = request.json['uid']
    allProducts = mongo.db.products
    prod = allProducts.find_one({'_id': ObjectId(id)})

    if prod:
        allProducts.delete_one(prod)
        return jsonify(message='Product Deleted Successfully'), 201
    return jsonify(message='Something went wrong'), 401


@app.route("/adminOrders", methods=['PUT'])
def adminOrders():
    uid = request.json['uid']
    oid = request.json['oid']
    allUsers = mongo.db.users
    user = allUsers.find_one({'_id': uid, "orders": {'_id': ObjectId(oid)}})
    if user:
        print(user)
        return 201
    return 401


@app.route("/logoutAdmin", methods=['POST'])
def logoutAdmin():
    allUsers = mongo.db.admins
    user = allUsers.find_one({'tokens.token': request.json['auth']})

    if user:
        user['tokens'] = []
        allUsers.save(user)
        return jsonify(message='Logout Successfully!'), 201
    return jsonify(message='Something went wrong!'), 401


if __name__ == '__main__':

    app.run(debug=True)
