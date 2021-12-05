from flask import Flask, Response, request
from flask_cors import CORS
import json
from requests_futures.sessions import FuturesSession
from typing import *

app = Flask(__name__)
CORS(app)
sess = FuturesSession()


USR_ADDR_PROPS = {
    'microservice': 'User/address microservice',
    'api': 'http://ec2-18-117-241-244.us-east-2.compute.amazonaws.com:5000/api/users',
    'fields': ('nameLast', 'nameFirst', 'email', 'addressID', 'password', 'gender')
}
USR_PREF_PROPS = {
    'microservice': 'User profile microservice',
    'api': 'http://ec2-3-145-83-228.us-east-2.compute.amazonaws.com:5000/api/profile',
    'fields': ('movie', 'hobby', 'book', 'music', 'sport', 'major', 'orientation')
}
SCHEDULE_PROPS = {
    'microservice': 'Scheduler microservice',
    # Using the local backend and remote DB for now. Code of this microservice still needs refinement
    # before next deployment to Elastic Beanstalk.
    'api': 'http://127.0.0.1:5003/api/availability/users',
    'fields': ('Id', 'Year', 'Month', 'Day', 'StartTime', 'EndTime')
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

    # Handle the scheduler microservice which has a different URL pattern
    props = SCHEDULE_PROPS
    data = project_req_data(req_data, props['fields'])
    if data is None:
        return 400, f"Missing data field(s) for {props['microservice']}"
    futures.append(
        sess.put(props['api'] + f"/{user_id}/{data['Id']}",
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
            "Id": string/int,
            "Year": string,
            "Month": string,
            "Day": string,
            "StartTime": string,
            "EndTime": string
        }
    """


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
