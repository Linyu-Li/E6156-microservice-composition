from flask import Flask, Response, request
from flask_cors import CORS
import json
from requests_futures.sessions import FuturesSession
from typing import *

app = Flask(__name__)
CORS(app)
sess = FuturesSession()

# TODO change apis below to AWS ones in deployment
USR_ADDR_PROPS = {
    'microservice': 'User/address microservice',
    'api': 'http://localhost:5001/users',
    'fields': ('nameLast', 'nameFirst', 'email', 'addressID', 'password', 'gender')
}
USR_PREF_PROPS = {
    'microservice': 'User profile microservice',
    'api': 'http://localhost:5002/profile',
    'fields': ('movie', 'hobby', 'book', 'music', 'sport', 'major', 'orientation')
}
SCHEDULE_PROPS = {
    'microservice': 'Scheduler microservice',
    'api': 'http://localhost:5003/availability/users',
    'fields': ('Year', 'Month', 'Day', 'StartTime', 'EndTime')
}
PROPS = (USR_ADDR_PROPS, USR_PREF_PROPS, SCHEDULE_PROPS)


def project_req_data(req_data: dict, props: tuple) -> dict:
    res = dict()
    for prop in props:
        if prop not in req_data:
            return None
        res[prop] = req_data[prop]
    return res


def async_request_microservices(req_data: dict,
                                user_id: Union[int, str],
                                headers: Dict) -> (int, str):
    futures = []
    for props in (USR_ADDR_PROPS, USR_PREF_PROPS):
        data = project_req_data(req_data, props['fields'])
        if data is None:
            return 400, f"Missing data field(s) for {props['microservice']}"
        futures.append(
            sess.put(props['api'] + f"/{user_id}",
                     data=json.dumps(data),
                     headers=headers))

    prop = SCHEDULE_PROPS
    for time_slot in req_data['timeSlots']:
        tid = time_slot['Id']
        t_data = project_req_data(time_slot, prop['fields'])
        if t_data is None:
            return 400, f"Missing field(s) in one of the request data for {prop['microservice']}"
        futures.append(
            sess.put(props['api'] + f"/{user_id}/{tid}",
                     data=json.dumps(t_data),
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


@app.route('/api/update/<user_id>', methods=['PUT'])
def update_info(user_id):
    if request.method != 'PUT':
        status_code = 405
        return Response(f"{status_code} - wrong method!", status=status_code, mimetype="application/json")
    req_data = request.get_json()
    status_code, message = async_request_microservices(req_data, user_id, request.headers)
    return Response(f"{status_code} - {message}", status=status_code, mimetype="application/json")
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
            "orientation": string,
            "timeSlots": [
                {
                    "Id": string/int,
                    "Year": string,
                    "Month": string,
                    "Day": string,
                    "StartTime": string,
                    "EndTime": string
                },
                {
                    "Id": string/int,
                    "Year": string,
                    "Month": string,
                    "Day": string,
                    "StartTime": string,
                    "EndTime": string
                },
                ...
            ]
        }
    """


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
