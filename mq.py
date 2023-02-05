#!/usr/bin/python3
# -*- coding: utf-8 -*-
import json
import os
import random
import sys
import time
# import traceback
import paho.mqtt.client as mqtt
from dateutil.parser import *
import psutil


def checkrun(proc_name):
    """
    Check if there is any running process that contains the given name processName.
    """
    # Iterate over the all the running process
    for proc in psutil.process_iter():
        try:
            # Check if process name contains the given name string.
            if proc_name.lower() in proc.name().lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False


enable_agi = checkrun('asterisk')

if enable_agi:
    import asterisk.agitb
    import asterisk.agi

    asterisk.agitb.enable(display=True, logdir='/var/log/asterisk/')
    agi = asterisk.agi.AGI()
    asterisk.agitb.enable(agi, True, '/var/log/asterisk')


def agiprint(varname='', varvalue=''):
    if enable_agi:
        agi.verbose(f'=============== Variable {varname} IS {varvalue} ===============')
    else:
        print(f'=============== Variable {varname} IS {varvalue} ===============')


def agiset(varname, varvalue):
    if enable_agi:
        agi.set_variable(varname, varvalue)
        agiprint(varname, varvalue)
    else:
        agiprint(varname, f'{varvalue} NOT SETTABLE')


def agiget(varname):
    if enable_agi:
        varvalue = agi.get_variable(varname)
        agiprint(varname, varvalue)
    else:
        agiprint(varname, 'NOT GETTABLE')


topic = str(sys.argv[1])
outtopic = f"{topic}Res"
mqttserver = os.environ.get("HOST", "192.168.1.26")
rand_id = random.randint(1_000_000, 9_999_999)
# print(rand_id)
# print(f"mqttserver is: {mqttserver}")

wait = True


def on_connect(cl, userdata, flags, rc):
    # print("Connected with result code " + str(rc))
    cl.subscribe(outtopic)


def on_message(cl, userdata, msg):
    global wait
    data = json.loads(msg.payload.decode())
    # print(data)  # converting the string back to a JSON object
    if data['id'] == rand_id and data['status'] == 'success':
        cl.loop_stop()
        cl.disconnect()
        if topic == "textToSpeech":
            # print(f"{data['text']}\n{data['filename']}")
            agiset('tts_text', data['text'])
            agiset('tts_filename', data['filename'])
            cl.loop_stop()
            cl.disconnect()
            wait = False
            sys.exit()

        if topic == "getOrder":
            order = data['data']
            # print(order)
            # agiset('client_fio', order['clientInfo']['fio'])
            # agiset('client_phone', order['clientInfo']['phone'])
            # agiset('client_email', order['clientInfo']['email'])
            agiset('client_cost', order['clientFullCost'])
            agiset('address_city', order['deliveryAddress']['city'])
            agiset('address', order['deliveryAddress']['inCityAddress']['address'])
            if order['robot']:
                agiset('robot', 'да')
            else:
                agiset('robot', 'нет')

            agiset('shop_name', order['marketName'])
            cl.loop_stop()
            cl.disconnect()
            wait = False
            sys.exit()

        if topic == "getOrderByPhone":
            order = data['data']
            agiset('client_fio', order['clientInfo']['fio'])
            agiset('client_phone', order['clientInfo']['phone'])
            agiset('client_email', order['clientInfo']['email'])
            agiset('client_cost', order['clientFullCost'])
            agiset('address_city', order['deliveryAddress']['city'])
            agiset('address', order['deliveryAddress']['inCityAddress']['address'])
            if order['robot']:
                agiset('robot', 'да')
            else:
                agiset('robot', 'нет')

            agiset('shop_name', order['marketName'])
            cl.loop_stop()
            cl.disconnect()
            wait = False
            sys.exit()

        if topic == "orderDoneRobot":
            order = data['data']
            agiprint('orderDoneRobot', order)
            cl.loop_stop()
            cl.disconnect()
            wait = False
            sys.exit()

        if topic == "orderRecallLater":
            order = data['data']
            agiprint('orderRecallLater', order)
            cl.loop_stop()
            cl.disconnect()
            wait = False
            sys.exit()

        if topic == "getNearDeliveryDatesIntervals":
            if data['data']:
                order_dates = []
                for order in data['data']:
                    begin_date = {}
                    if order['quotas']['available'] > 0:
                        order_date = parse(f"{order['date']}", ignoretz=True)
                        # print(order_date)
                        begin_date['date'] = order_date.strftime('%d.%m.%Y')
                        # print(begin_date['date'])
                        begin_date['day'] = order_date.strftime('%d')
                        begin_date['month'] = order_date.strftime('%m')
                        begin_date['year'] = order_date.strftime('%Y')
                        order_dates.insert(len(order_dates), begin_date)

                agiset('order_begin_date', order_dates[0]['date'])
                agiset('order_end_date', order_dates[-1]['date'])

                dates = []
                for index in order_dates:
                    dates.append(index['date'])
                agiset('order_avail_date', ','.join(dates))
                # print(', '.join(dates))
            else:
                # print("no free date")
                agiset('no_free_date', 'да')

        cl.loop_stop()
        cl.disconnect()
        wait = False
        sys.exit()
        # print("message recived")
    # else:
    #     agiset(f'{topic}_data_error', data['errorMessage'])
    #     agiset(f'data_error', True)
    #     # print(data['errorMessage'])
    #     cl.loop_stop()
    #     cl.disconnect()
    #     wait = False
    #     sys.exit()


def switch(topic_name):
    data = {}
    if topic_name == "orderDoneRobot":
        data['orderId'] = str(sys.argv[2])
        data['id'] = rand_id
        data['callId'] = str(sys.argv[3])
        data['robotDeliveryDate'] = str(sys.argv[4])
        payload = json.dumps(data, ensure_ascii=False)
        agiprint('send', f"{topic_name} payload: {payload}")
        client.publish(topic, payload)
    elif topic_name == "orderRecallLater":
        data['orderId'] = str(sys.argv[2])
        data['id'] = rand_id
        data['callId'] = str(sys.argv[3])
        payload = json.dumps(data, ensure_ascii=False)
        agiprint('send', f"{topic_name} payload: {payload}")
        client.publish(topic, payload)
    elif topic_name == "getOrder":
        data['orderId'] = str(sys.argv[2])
        data['id'] = rand_id
        payload = json.dumps(data, ensure_ascii=False)
        agiprint('send', f"{topic_name} payload: {payload}")
        client.publish(topic, payload)
    elif topic_name == "getOrderByPhone":
        data['phone'] = str(sys.argv[2])
        data['id'] = rand_id
        payload = json.dumps(data, ensure_ascii=False)
        agiprint('send', f"{topic_name} payload: {payload}")
        client.publish(topic, payload)
    elif topic_name == "getNearDeliveryDatesIntervals":
        data['orderId'] = str(sys.argv[2])
        data['id'] = rand_id
        payload = json.dumps(data, ensure_ascii=False)
        agiprint('send', f"{topic_name} payload: {payload}")
        client.publish(topic, payload)
    elif topic_name == "textToSpeech":
        data['id'] = rand_id
        data['text'] = str(sys.argv[2])
        payload = json.dumps(data, ensure_ascii=False)
        agiprint('send', f"{topic_name} payload: {payload}")
        client.publish(topic, payload)


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(mqttserver)
client.subscribe(outtopic)
client.loop_start()
switch(topic)
i = 0
while wait:
    time.sleep(0.1)
    i += 1
    if i == 60:
        agiset('mqtt_error', 'timeout')
        break


client.loop_stop()
client.disconnect()
sys.exit()
