from flask import Flask, Response, request
from flask_cors import CORS
import json
from typing import *
import requests

app = Flask(__name__)
CORS(app)

# TODO change apis below to AWS ones in deployment
USR_ADDR_PROPS = {
    'microservice': 'User/address microservice',
    'api': 'http://localhost:5001/api/users',
    'fields': ('nameLast', 'nameFirst', 'email', 'addressID', 'password', 'gender')
}
USR_PREF_PROPS = {
    'microservice': 'User profile microservice',
    'api': 'http://localhost:5002/api/profile',
    'fields': ('movie', 'hobby', 'book', 'music', 'sport', 'major', 'orientation')
}
SCHEDULE_PROPS = {
    'microservice': 'Scheduler microservice',
    'api': 'http://localhost:5003/api/availability/users',
    'fields': 'Id'
}



def project_req_data(req_data: dict, props: tuple) -> dict:
    res = dict()
    if type(props) is tuple:
        for prop in props:
            if prop not in req_data:
                return None
            res[prop] = req_data[prop]
        return res
    else:
        res['Id'] = req_data['Id']
        return res

def sync_request_microservices(req_data: dict,
                                headers: Dict) -> (int, str):
    # register users
    register_data = project_req_data(req_data, USR_ADDR_PROPS['fields'])
    if register_data is None:
        return 400, f"Missing data field(s) for {USR_ADDR_PROPS['microservice']}"
    user_res = requests.post(USR_ADDR_PROPS['api'],
                        data=json.dumps(register_data),
                        headers=headers)

    if user_res.status_code != 201:
        return 400, "/user goes wrong, please check"

    res_str = user_res.json()
    uid = res_str.split()[4]

    # create preference and timeslot
    prop = USR_PREF_PROPS
    data = project_req_data(req_data, prop['fields'])
    if data is None:
        return 400, f"Missing data field(s) for {prop['microservice']}"
    data['id'] = uid
    pref_res = requests.post(prop['api'],
                  data=json.dumps(data),
                  headers=headers)

    if pref_res.status_code != 201:
        return 400, "/profile goes wrong, please check"

    prop = SCHEDULE_PROPS
    data = project_req_data(req_data, prop['fields'])
    schedule_res = requests.post(prop['api'] + f"/{uid}",
                  data=json.dumps(data),
                  headers=headers)

    if schedule_res.status_code != 201:
        return 400, "/availability goes wrong, please check"

    return 200, "User info created successfully!"


@app.route('/api/create', methods=['POST'])
def update_info():
    if request.method != 'POST':
        status_code = 405
        return Response(f"{status_code} - wrong method!", status=status_code, mimetype="application/json")
    req_data = request.get_json()
    status_code, message = sync_request_microservices(req_data, request.headers)
    return Response(f"{status_code} - {message}", status=status_code, mimetype="application/json")
    """
        Request JSON format example:
        {
            "nameLast": "Linyu",
            "nameFirst": "Li",
            "email": "ll3465@columbia.edu",
            "addressID":"1",
            "password": "test",
            "gender": "test",
            "movie": "test",
            "hobby": "test",
            "book": "test",
            "music": "test",
            "sport": "test",
            "major": "test",
            "orientation": "test",
            "Id": "12"
        }
    """


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5004)