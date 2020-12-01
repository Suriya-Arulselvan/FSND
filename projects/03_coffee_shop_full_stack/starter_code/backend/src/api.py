import os
import sys
from flask import Flask, request, jsonify, abort
from sqlalchemy import exc
import json
from jsonschema import validate, ValidationError

from flask_cors import CORS

from .database.models import db,db_drop_and_create_all, setup_db, Drink, dbSessionRollback, dbSessionClose
from .auth.auth import AuthError, requires_auth

app = Flask(__name__)
setup_db(app)
CORS(app, resource={r"/*": {"origins":"*"}})

'''
$TODO uncomment the following line to initialize the datbase
!! NOTE THIS WILL DROP ALL RECORDS AND START YOUR DB FROM SCRATCH
!! NOTE THIS MUST BE UNCOMMENTED ON FIRST RUN
'''
#db_drop_and_create_all()

def isLongRecipe(longRecipe):
    valid = True
    for sub in longRecipe:
        if (("color" not in sub) or ("name" not in sub) or ("parts" not in sub)):
            valid = False 
    return valid

## ROUTES
'''
$TODO implement endpoint
    GET /drinks
        it should be a public endpoint
        it should contain only the drink.short() data representation
    returns status code 200 and json {"success": True, "drinks": drinks} where drinks is the list of drinks
        or appropriate status code indicating reason for failure
'''
@app.route("/drinks")
def getDrinks():
    drinks = Drink.query.order_by(Drink.id).all()

    if len(drinks) == 0:
        abort(404)

    displayDrinks = [drink.short() for drink in drinks]
    return jsonify({
        "success": True,
        "drinks": displayDrinks
    }), 200


'''
$TODO implement endpoint
    GET /drinks-detail
        it should require the 'get:drinks-detail' permission
        it should contain the drink.long() data representation
    returns status code 200 and json {"success": True, "drinks": drinks} where drinks is the list of drinks
        or appropriate status code indicating reason for failure
'''

@app.route("/drinks-detail")
@requires_auth('get:drinks-detail')
def getDrinkskDetails(oayload):
    drinks = Drink.query.order_by(Drink.id).all()

    if len(drinks) == 0:
        abort(404)

    displayDrinks = [drink.long() for drink in drinks]
    return jsonify({
        "success": True,
        "drinks": displayDrinks
    }), 200

'''
$TODO implement endpoint
    POST /drinks
        it should create a new row in the drinks table
        it should require the 'post:drinks' permission
        it should contain the drink.long() data representation
    returns status code 200 and json {"success": True, "drinks": drink} where drink an array containing only the newly created drink
        or appropriate status code indicating reason for failure
'''
@app.route("/drinks", methods=["POST"])
@requires_auth('post:drinks')
def createDrink(payload):
    payload = request.json
    error = False
    body = {}
    try:
        title = payload["title"]
        valid = isLongRecipe(payload["recipe"])
        if valid:
            recipe = json.dumps(payload["recipe"])
        else:
            abort(400)
        drink = Drink(title=title, recipe=recipe)
        drink.insert()
        body = drink.long()
    except Exception:
        dbSessionRollback()
        error = True
        print(sys.exc_info())
    finally:
        dbSessionClose()
        
    if error:
        abort(400)
    else:
        return jsonify({
            "success":True,
            "drinks": [body]
        }), 200


'''
$TODO implement endpoint
    PATCH /drinks/<id>
        where <id> is the existing model id
        it should respond with a 404 error if <id> is not found
        it should update the corresponding row for <id>
        it should require the 'patch:drinks' permission
        it should contain the drink.long() data representation
    returns status code 200 and json {"success": True, "drinks": drink} where drink an array containing only the updated drink
        or appropriate status code indicating reason for failure
'''
@app.route("/drinks/<int:index>", methods=['PATCH'])
@requires_auth('patch:drinks')
def editDrink(payload, index):
    drink = Drink.query.get(index)
    if drink is None:
        abort(404)
    
    data = request.json
    error = False
    body = {}
    try: 
        title = data.get("title")
        drink.title = title
        if data.get("recipe") is not None:
            valid = isLongRecipe(data.get("recipe"))
            if valid:
                drink.recipe = json.dumps(data["recipe"])
            else:
                abort(400)
        drink.update()
        body = drink.long()
    except Exception:
        dbSessionRollback()
        error = True
        print(sys.exc_info())
    finally:
        dbSessionClose()
    
    if error:
        abort(400)
    else:
        return jsonify({
            "success" : True,
            "drinks": [body]
        }), 200


    

'''
$TODO implement endpoint
    DELETE /drinks/<id>
        where <id> is the existing model id
        it should respond with a 404 error if <id> is not found
        it should delete the corresponding row for <id>
        it should require the 'delete:drinks' permission
    returns status code 200 and json {"success": True, "delete": id} where id is the id of the deleted record
        or appropriate status code indicating reason for failure
'''



@app.route("/drinks/<drink_id>", methods=["DELETE"])
@requires_auth("delete:drinks")
def delete_drink(payload, drink_id):
    error = False
    drink = Drink.query.get(drink_id)
    if drink is None: 
        abort(404)
    try:
        drink = Drink.query.get(drink_id)
        drink.delete()
    except Exception:
        dbSessionRollback()
        error = True
        print(sys.exc_info())
    finally: 
        dbSessionClose()
    
    if error:
        abort(400)
    else:
        return jsonify({
            "succes" : True,
            "delete" : drink_id
        }), 200


## Error Handling
'''
Example error handling for unprocessable entity
'''
@app.errorhandler(422)
def unprocessable(error):
    return jsonify({
                    "success": False, 
                    "error": 422,
                    "message": "unprocessable"
                    }), 422

'''
$TODO implement error handlers using the @app.errorhandler(error) decorator
    each error handler should return (with approprate messages):
             jsonify({
                    "success": False, 
                    "error": 404,
                    "message": "resource not found"
                    }), 404

'''

'''
$TODO implement error handler for 404
    error handler should conform to general task above 
'''
@app.errorhandler(404)
def not_found(error):
    return jsonify({"success": False, "error": 404, "message": "Resource not found"}),404

@app.errorhandler(400)
def bad_request(error):
    return jsonify({"success": False, "error": 400, "message": "Bad Request"}),400

@app.errorhandler(500)
def bad_request(error):
    return jsonify({"success": False, "error": 500, "message": "Internal Server Error"}),500
'''
$TODO implement error handler for AuthError
    error handler should conform to general task above 
'''
@app.errorhandler(AuthError)
def handle_auth_error(ex):
    response = jsonify(ex.error)
    response.status_code = ex.status_code
    return response

