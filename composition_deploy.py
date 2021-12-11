from flask import Flask, Response, request
from flask_cors import CORS
import json
import requests
from requests_futures.sessions import FuturesSession
from typing import *


app = Flask(__name__)
CORS(app)
sess = FuturesSession()


USR_ADDR_PROPS = {
    'microservice': 'User/address microservice',
    # 'api': 'http://ec2-18-117-241-244.us-east-2.compute.amazonaws.com:5000/api/users',
    'api': 'http://127.0.0.1:5001/api/users',
    'fields': ('nameLast', 'nameFirst', 'email', 'address', 'postcode', 'password', 'gender')
}
USR_PREF_PROPS = {
    'microservice': 'User profile microservice',
    # 'api': 'http://ec2-3-145-83-228.us-east-2.compute.amazonaws.com:5000/api/profile',
    'api': 'http://127.0.0.1:5002/api/profile',
    'fields': ('movie', 'hobby', 'book', 'music', 'sport', 'major', 'orientation')
}
PROPS = (USR_ADDR_PROPS, USR_PREF_PROPS)

"""
Request JSON format:
{
    "nameLast": string,
    "nameFirst": string,
    "email": string,
    "addressID": string/int,
    "password": string,
    "gender": string,
    "movie": string,
    "hobby": string,
    "book": string,
    "music": string,
    "sport": string,
    "major": string,
    "orientation": string
}
"""

def project_req_data(req_data: dict, props: tuple) -> dict:
    res = dict()
    for prop in props:
        if prop not in req_data:
            return None
        res[prop] = req_data[prop]
    return res


def async_request_microservices(req_data: dict,
                                data_id: Union[int, str],
                                headers: Dict) -> (int, str):
    futures = []
    for props in (USR_ADDR_PROPS, USR_PREF_PROPS):
        data = project_req_data(req_data, props['fields'])
        if data is None:
            return 400, f"Missing data field(s) for {props['microservice']}"
        futures.append(
            sess.put(props['api'] + f"/{data_id}",
                     data=json.dumps(data),
                     headers=headers))

    for i, future in enumerate(futures):
        microservice = PROPS[min(i, 2)]['microservice']
        res = future.result()
        if res is None:
            return 408, f"{microservice} did not response."
        elif not res.ok:
            return res.status_code, \
                   f"Response from the {microservice} is not OK."
    return 200, "User info updated successfully!"


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

    # create preference
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

    return 200, "User info created successfully!"


@app.route('/api/update/<user_id>', methods=['PUT'])
def update_info(user_id):
    req_data = request.get_json()
    status_code, message = async_request_microservices(req_data, user_id, request.headers)
    return Response(f"{status_code} - {message}", status=status_code, mimetype="application/json")


@app.route('/api/create', methods=['POST'])
def create_info():
    req_data = request.get_json()
    status_code, message = sync_request_microservices(req_data, request.headers)
    return Response(f"{status_code} - {message}", status=status_code, mimetype="application/json")


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
