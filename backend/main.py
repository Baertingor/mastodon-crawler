import csv
import logging
from io import StringIO

import pymongo
import requests
from flask import Flask, Response, make_response, request

app = Flask(__name__)

bind_to = {'hostname': "0.0.0.0", 'port': 8080}


@app.route('/ping', methods=['GET'])
def health_check():
    return Response('pong', status=200)


@app.route('/get_followings', methods=['Get'])
def get_followings():
    param_value = request.args.get('param')
    username = param_value.split('@')[1]
    instance = param_value.split('@')[2]
    response = requests.get(f"https://{instance}/api/v1/accounts/lookup?acct={username}")
    data = response.json()

    base_url = f"https://{instance}/api/v1/accounts/{data['id']}/following"
    account = get_account_by_id(f'{instance}', data['id'])
    mycoll = mydb[f'{param_value}']
    next_accounts = {}

    mycoll.update_one(
        {'user_id': account['user_id']},
        {'$set': account},
        upsert=True
    )

    while True:
        response = requests.get(base_url)

        if response.status_code != 200:
            return Response(f"handle not found", status=400)

        header = response.headers.get("Link")
        data = response.json()
        parsed_data = parse_records(data, account)

        for record in parsed_data:
            if record['bot'] is False:
                try:
                    instance = record['instance']
                    username = record['username']
                    url = f"https://{instance}/api/v1/accounts/lookup?acct={username}"
                    response = requests.get(url)
                    data = response.json()
                    record['user_id'] = data['id']
                    next_accounts[record['target']] = data['id']
                except Exception as e:
                    logging.debug(e)

        bulk_operation = [
            pymongo.UpdateOne(
                {'user_id': record['user_id']},
                {'$set': record},
                upsert=True
            )
            for record in parsed_data
        ]
        try:
            mycoll.bulk_write(bulk_operation)
        except Exception as e:
            print(e)

        link = parse_link_header(header)
        next_url = link.get('next')

        if next_url:
            base_url = next_url
            print(base_url)
        else:
            print("break")
            break

    logging.debug(f"account search finished and the length of next accounts: {len(next_accounts)}")
    for key, user_id in next_accounts.items():
        instance = key.split('@')[0]
        logging.debug(f"Next account: {instance} and username: {user_id} and key:{key}")
        get_next_accounts(instance, user_id, mycoll)
    logging.debug("next accounts finished")

    csv_data = make_csv(mycoll)
    response = make_response(csv_data.read())
    response.headers['Content-Disposition'] = f'attachment; filename=list_out.csv'
    response.headers['Content-type'] = 'text/csv'

    return response


def make_csv(my_collection):
    data = my_collection.find({}, {"_id": 0,
                                   "followers_count": 1,
                                   "instance": 1,
                                   "username": 1,
                                   "source": 1,
                                   "target": 1,
                                   "id": 1})

    csv_data = StringIO()
    csv_writer = csv.writer(csv_data)
    csv_writer.writerow(['followers_count', 'instance', 'username', 'source', 'target', 'id'])  # Header
    for entry in data:
        csv_writer.writerow(entry.values())

    csv_data.seek(0)

    return csv_data


def get_next_accounts(instance, user_id, mycoll):
    base_url = f"https://{instance}/api/v1/accounts/{user_id}/following"
    base_account = f"https://{instance}/api/v1/accounts/{user_id}"

    try:
        response = requests.get(base_account)
        if response.status_code != 200:
            return
        account = get_account_by_id(instance, user_id)
        while True:
            response = requests.get(base_url)

            if response.status_code != 200:
                return Response(f"handle not found", status=400)

            header = response.headers.get("Link")
            data = response.json()
            parsed_data = parse_records(data, account)

            for record in parsed_data:
                try:
                    mycoll.insert_one(record)
                except Exception as e:
                    print(e)

            link = parse_link_header(header)
            next_url = link.get('next')

            if next_url:
                base_url = next_url
                print(base_url)
            else:
                break
    except Exception as e:
        print(e)


def parse_records(crawled_data, source_account):
    parsed_records = []
    f"length of crawled_data: {len(crawled_data)}"
    try:
        for record in crawled_data:
            url = record['url']
            # retrieve instance from URL
            instance = url.split('/')[2]
            parsed_records.append({
                'id': instance + '@' + record['username'],
                'source': source_account['source'],
                'target': instance + '@' + record['username'],
                'username': record['username'],
                'instance': instance,
                'discoverable': record['discoverable'],
                'bot': record['bot'],
                'user_id': record['id'],
                'url': record['url'],
                'followers_count': record['followers_count']
            })
    except Exception as e:
        print(e)

    return parsed_records


def get_account_by_id(instance, user_id):
    f"""get_account: {instance}, {user_id}"""
    base_account = f"https://{instance}/api/v1/accounts/{user_id}"
    response = requests.get(base_account)
    data = response.json()
    parsed_record = {}

    try:
        url = data['url']
        # retrieve instance from URL
        instance = url.split('/')[2]
        username = url.split('/')[3]
        parsed_record = {
            'id': f'{instance}{username}',
            'source': f'{instance}{username}',
            'target': f'{instance}{username}',
            'username': data['username'],
            'instance': instance,
            'discoverable': data['discoverable'],
            'bot': data['bot'],
            'user_id': data['id'],
            'url': data['url'],
            'followers_count': data['followers_count']
        }
    except Exception as e:
        print(e)
    return parsed_record


def parse_link_header(link_header):
    links = {}
    if link_header:
        link_parts = link_header.split(', ')
        for part in link_parts:
            url, rel = part.split('; ')
            url = url[1:-1]
            rel = rel[5:-1]
            links[rel] = url
    return links


if __name__ == "__main__":
    myClient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myClient["mydatabase"]

    level = logging.DEBUG
    fmt = '%(asctime)s %(levelname)s %(message)s'
    logging.basicConfig(format=fmt, level=level)
    app.run(host=bind_to['hostname'], port=int(bind_to['port']), debug=True)
