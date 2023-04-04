import psycopg2
import requests
import json
import ast
from config import host, user, password, db_name


def getCookies() -> dict:
    with open("cookies", "r") as f:
        data = f.read()
        data_dict = ast.literal_eval(data)
        return data_dict


def getHeaders() -> dict:
    with open("headers", "r") as f:
        data = f.read()
        data_dict = ast.literal_eval(data)
        return data_dict


def getCodes(city_: str) -> list[str]:
    try:
        connection = psycopg2.connect(
            host=host,
            user=user,
            password=password,
            database=db_name
        )
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT * FROM codes WHERE city = '{city_}'")
            s = cursor.fetchone()
            if s and len(s) > 0:
                return [s[1], s[2]]

        headers = {
            'sec-ch-ua': '".Not/A)Brand";v="99", "Google Chrome";v="103", "Chromium";v="103"',
            'Accept': 'application/json, text/plain, */*',
            'Referer': 'https://ticket.rzd.ru/searchresults/v/1/5a323c29340c7441a0a556bb/5a13ba89340c745ca1e7ebbe/2023-05-11',
            'sec-ch-ua-mobile': '?0',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36',
            'sec-ch-ua-platform': '"Linux"'
        }
        city_b = str(bytes(city_, encoding='utf-8'))
        city_b = city_b.replace(r'\x', '%')[2:-1]
        url = "https://ticket.rzd.ru/api/v1/suggests?GroupResults=true&RailwaySortPriority=true&Query=" + city_b
        data = requests.get(url, headers=headers)
        data = json.loads(data.text)
        with connection.cursor() as cursor:
            cursor.execute(
                f"INSERT INTO codes (city, node_id, express_code) VALUES ('{city_}', '{data['city'][0]['nodeId']}', '{data['city'][0]['expressCode']}')")
            connection.commit()
        return [data['city'][0]['nodeId'], data['city'][0]['expressCode']]

    except (Exception, psycopg2.Error) as error:
        print(error)
    finally:
        if connection:
            connection.close()


def generatePOSTdata(origin: str, destination: str, dep_date: str) -> dict:
    data = {
        'Origin': origin,
        'Destination': destination,
        'DepartureDate': dep_date + 'T00:00:00',
        'TimeFrom': 0,
        'TimeTo': 24,
        'CarGrouping': 'DontGroup',
        'GetByLocalTime': True,
        'SpecialPlacesDemand': 'StandardPlacesAndForDisabledPersons'
    }
    return data


def getTickets(origin_city: str, destination_city: str, dep_time: str) -> str:
    cookies = getCookies()
    headers = getHeaders()

    origin = getCodes(origin_city)[1]
    destination = getCodes(destination_city)[1]
    json_data = generatePOSTdata(origin, destination, dep_time)
    params = {
        'service_provider': 'B2B_RZD',
    }
    response = requests.post(
        'https://ticket.rzd.ru/apib2b/p/Railway/V1/Search/TrainPricing',
        params=params,
        cookies=cookies,
        headers=headers,
        json=json_data,
    )
    return response.text


def parseTickets(data: str) -> str:
    data = json.loads(data)
    trains = []
    for i in range(len(data['Trains'])):
        trains.append({})

    for train in range(len(trains)):
        trains[train]['dep_time'] = data['Trains'][train]['DepartureDateTime']
        trains[train]['arr_time'] = data['Trains'][train]['ArrivalDateTime']
        for car_group in range(len(data['Trains'][train]['CarGroups'])):
            carGroup = data['Trains'][train]['CarGroups'][car_group]
            if carGroup['CarTypeName'] == "БАГАЖ":
                continue
            if carGroup['CarTypeName'] not in trains[train]:
                trains[train][carGroup['CarTypeName']] = [int(10e9), 0]
            trains[train][carGroup['CarTypeName']][0] = min(carGroup['MinPrice'], trains[train][carGroup['CarTypeName']][0])
            quantity = carGroup['LowerPlaceQuantity'] + carGroup['UpperPlaceQuantity'] + carGroup['LowerSidePlaceQuantity'] + carGroup['UpperSidePlaceQuantity']
            trains[train][carGroup['CarTypeName']][1] += quantity

    ans = ""
    for train in range(len(trains)):
        s = f"Train {train + 1}:\nDeparture Time: {trains[train]['dep_time'].replace('T', ' ')}\nArrival Time: {trains[train]['arr_time'].replace('T', ' ')}\n"
        if 'ПЛАЦ' in trains[train]:
            s += f"Plazkart: minimum price {trains[train]['ПЛАЦ'][0]}, {trains[train]['ПЛАЦ'][1]} seats\n"
        if 'КУПЕ' in trains[train]:
            s += f"Сompartment: minimum price {trains[train]['КУПЕ'][0]}, {trains[train]['КУПЕ'][1]} seats\n"
        if 'СВ' in trains[train]:
            s += f"Sleeping: minimum price {trains[train]['СВ'][0]}, {trains[train]['СВ'][1]} seats\n"
        if 'ЛЮКС' in trains[train]:
            s += f"Luxuary: minimum price {trains[train]['ЛЮКС'][0]}, {trains[train]['ЛЮКС'][1]} seats\n"

        ans += s + '\n'

    return ans
