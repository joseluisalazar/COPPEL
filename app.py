from unittest import result
from urllib import response
from flask import Flask,render_template,make_response,jsonify,request,Response
import pymongo, requests, json,secrets,hashlib,base64

app = Flask(__name__)

PORT = 3288
HOST = '0.0.0.0'
TS = 1
PRIVATE_KEY = 'c43947b32a437c6f0b9efa93739678e4eef84f33'
PUBLIC_KEY = 'e4dc583873aebcc0e221671f566c3aca'
HASH = '29448c59895ee56561a622f4f4815c07'
URL_BASE = "https://gateway.marvel.com:443/v1/public/"

@app.route("/", methods=["GET"])
def home():
    return "<h1> API EDITORIAL </h1>";

@app.route("/searchComics/", methods=["GET"])
def searchComics():
    try:
        search          = request.args.get("search",None)
        only            = request.args.get("only",None)
        data            = []
        url_characters  = f"{URL_BASE}characters?apikey={PUBLIC_KEY}&hash={HASH}&ts={TS}"
        url_comics      = f"{URL_BASE}comics?apikey={PUBLIC_KEY}&hash={HASH}&ts={TS}"
        
        if search:
            url_characters += "&nameStartsWith=" + search
            url_comics     += "&titleStartsWith=" + search
    
        url_characters += "&orderBy=name"
        url_comics     += "&orderBy=title"

        if(only == "characters" or only == None):
            response_characters = requests.get(url_characters)
            if response_characters.status_code == 200:
                response_json = json.loads(response_characters.text)

                for i in response_json["data"]["results"]:

                    element = {
                        "id"    : i["id"],
                        "name"  : i["name"],
                        "image" : i["thumbnail"]["path"] + "." + i["thumbnail"]["extension"],
                        "appearances" : i["comics"]["available"]
                    }

                    data.append(element)

        if(only == "comics" or only == None):
            response_comics     = requests.get(url_comics)
            if response_comics.status_code == 200:
                response_json = json.loads(response_comics.text)

                for i in response_json["data"]["results"]:

                    element = {
                        "id"    : i["id"],
                        "title"  : i["title"],
                        "image" : i["thumbnail"]["path"] + "." + i["thumbnail"]["extension"],
                        "onsaleDate" : i["dates"][0]["date"]
                    }

                    data.append(element)

        return json.dumps(data), 200, {'ContentType':'application/json'}      

    except Exception as e:
        return json.dumps({'success':False, 'message': str(e)}), 400, {'ContentType':'application/json'}    


@app.route("/users/", methods=["GET"])
def users():
    try:
        db      = dbConnect()
        records = db.users.find({})
        users = []
        for record in records:
            user = {
                "id": str(record['_id']),
                "name": record['name'],
                "age": record['age'],
                "token": record['token'],
        }

        users.append(user)

        return json.dumps(users), 200, {'ContentType':'application/json'}      

    except Exception as e:
        return json.dumps({'success':False, 'message': str(e)}), 400, {'ContentType':'application/json'}


@app.route("/users/register", methods=["POST"])
def userAdd():
    try:
        db          = dbConnect()
    
        name        = request.args.get("name","")
        email       = request.args.get("email","")
        age         = request.args.get("age","")
        password    = request.args.get("password","")
        token       = secrets.token_hex(20)

        if(email == "" or password == ""):
            raise Exception("email and password are required")

        pwd_hash = hashlib.md5(password.encode()).hexdigest()
        user     = db.users.find_one({ "email": email, "password" : pwd_hash})

        if(user):
            raise Exception("User register")

        document = {
            "name"  : name,
            "email" : email,
            "age"   : age,
            "password" : hashlib.md5(password.encode()).hexdigest(),
            "token" : token,
        }

        user = db.users.insert_one(document)

        response = {
            'success': True, 
            'token': token
        }

        return json.dumps(response), 200, {'ContentType':'application/json'}      

    except Exception as e:
        return json.dumps({'success':False, 'message': str(e)}), 400, {'ContentType':'application/json'}      


@app.route("/users/login", methods=["POST"])
def login():
    try:
        db          = dbConnect()
    
        email       = request.args.get("email","")
        password    = request.args.get("password","")

        if(email == "" or password == ""):
            raise Exception("email and password are required")

        pwd_hash = hashlib.md5(password.encode()).hexdigest()
        user     = db.users.find_one({ "email": email, "password" : pwd_hash})

        if(user == None):
            raise Exception("User invalid")

        response = {
            'success': True, 
            'name'   : user.get('name'),
            'age'    : user.get('age'),
            'email'  : user.get('email'),
            'token'  : user.get('token') 
        }

        return json.dumps(response), 200, {'ContentType':'application/json'}      

    except Exception as e:
        return json.dumps({'success':False, 'message': str(e)}), 400, {'ContentType':'application/json'}      

@app.route("/addToLayaway/", methods=["POST"])
def layaway():
    try:
        db          = dbConnect()
    
        token       = request.args.get("token","")
        comicId     = request.args.get("comicId","")

        if(token == ""):
            raise Exception("token is required")

        if(comicId == ""):
            raise Exception("comic id is required")

        user     = db.users.find_one({ "token": token})

        if(user == None):
            raise Exception("token invalid")

        url_comic        = f"{URL_BASE}comics/{comicId}?apikey={PUBLIC_KEY}&hash={HASH}&ts={TS}" 
        response_comics  = requests.get(url_comic)

        if(response_comics.status_code == 404):
            raise Exception("Comic not found ID:" + comicId)

        document = {
            "user"  : user.get('_id'),
            "comic" : comicId,
            "created_at"   : "",
        }

        layaway = db.layaway.insert_one(document)

        response = {
            'success': True
        }

        return json.dumps(response), 200, {'ContentType':'application/json'}      

    except Exception as e:
        return json.dumps({'success':False, 'message': str(e)}), 400, {'ContentType':'application/json'}

@app.route("/getLayawayList/", methods=["GET"])
def layawaylist():
    try:
        db          = dbConnect()
        data        = []
        token       = request.args.get("token","")

        if(token == ""):
            raise Exception("token is required")

        user     = db.users.find_one({ "token": token})

        if(user == None):
            raise Exception("token invalid")

        layaways = db.layaway.find({'user': user.get('_id')})
       
        for record in layaways:

            comicId          = record['comic']
            url_comic        = f"{URL_BASE}comics/{comicId}?apikey={PUBLIC_KEY}&hash={HASH}&ts={TS}" 
            response_comics  = requests.get(url_comic)
            response_comic   = json.loads(response_comics.text)

            layaway = {
                "id"         : response_comic["data"]["results"][0]["id"],
                "title"      : response_comic["data"]["results"][0]["title"],
                "image"      : response_comic["data"]["results"][0]["thumbnail"]["path"] + "." + response_comic["data"]["results"][0]["thumbnail"]["extension"],
                "onsaleDate" : response_comic["data"]["results"][0]["dates"][0]["date"]
            }

            data.append(layaway)

        response = {
            'success': True,
            'comics' : data
        }

        return json.dumps(response), 200, {'ContentType':'application/json'}      

    except Exception as e:
        return json.dumps({'success':False, 'message': str(e)}), 400, {'ContentType':'application/json'} 


def dbConnect():
    try:
        client = pymongo.MongoClient("mongodb+srv://Test:VOIm0IxVX0Xpx7Qn@cluster0.s8bjr.mongodb.net/cp_comics?retryWrites=true&w=majority")
        db = client.cp_comics
        return db
    except pymongo.errors.ConnectionFailure:
        print('error connection to database') 
    return db     

if __name__ == "__main__":
    print("server running in port: %s"%(PORT))
    app.run(host=HOST,port=PORT,debug=True)