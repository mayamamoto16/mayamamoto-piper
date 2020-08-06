#!/usr/bin/env python
# coding: UTF-8
import ADC0832
import time
import math
import requests
import RPi.GPIO as GPIO
import paho.mqtt.client as mq # MQTT
import ssl
import json
from time import sleep
from datetime import datetime as dt


GPIO.setmode(GPIO.BOARD)       # Numbers pins by physical location
GPIO.setup(15, GPIO.OUT)       # Set pin mode as output
GPIO.output(15, GPIO.HIGH)     # Set pin to high(+3.3V) to off the led

i = 1
Gas_buf = 0
Gas_R0 = 60
ratio = 0
BAC = 0

endpoint = "ajbpqgdbygd2e-ats.iot.ap-northeast-1.amazonaws.com" #AWSのエンドポイント
port = 8883 #AWSのポート
topic = "count/pub" # カウント数をRaspberryPi to AWS
cert = "./cert/1479350817-certificate.pem.crt" #モノの証明書
key = "./cert/1479350817-private.pem.key" #プライベートキー
rootCA = "./cert/AmazonRootCA1.pem" #Amazonルート証明書

def init():
	ADC0832.setup()

init()

for i in range(31):
	res = ADC0832.getResult()
	GasConcentration = res
#	print 'analog value: %03d  Gas concentration: %d' %(res, Gas_concentration)
	time.sleep(0.1)

	if i != 0:
		Gas_buf = Gas_buf + GasConcentration
		print (GasConcentration)
	else:
		print ("skip ok")

def if_buf(Gas_buf):
	token = "72uIbiNQLXDoK6ZFsOSqR6Soyfxpq7g8McPUweOB3zo"
	url = "https://notify-api.line.me/api/notify"
	headers = {"Authorization": "Bearer " + token}

	client = mq.Client(protocol=mq.MQTTv311) #初期化
	client.tls_set(ca_certs=rootCA, certfile=cert, keyfile=key, #TLS通信のセット
			cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2)
	client.connect(endpoint, port=port, keepalive=60) #AWS IoTに接続
	print("RaspberryPi to AWS Start")

	if Gas_buf == 0:
		print ("Alcohol is not detected")

		payload = {"message": "Alcohol is not detected"}
		requests.post(url, headers=headers, data=payload)

		now = dt.now()
		message = {"Date":"{0:%Y-%m-%d}".format(now),
				"Time":"{0:%H:%M:%S}".format(now),
				"message":"Alcohol is not detected",
				 "count":Gas_buf}
		client.publish(topic, json.dumps(message)) #AWS IoTに送信(Publish)
		time.sleep(5)
		client.disconnect()            # 停止時にdisconnect

	else:
		for i in range(1,6):
			GPIO.output(15, GPIO.LOW)  # led on
			time.sleep(0.2)

			GPIO.output(15, GPIO.HIGH) # led off
			time.sleep(0.2)
		GPIO.output(15, GPIO.HIGH)     # led off
		GPIO.cleanup()                 # Release resource

		Gas_buf = Gas_buf / 30
		ratio = Gas_buf/Gas_R0
		ratio = math.log10(ratio)
		BAC = pow(10,-1*((ratio+0.2391)/0.6008))
		BAC = BAC * 2
		BAC = ('{:.4f}'.format(BAC))
		print (BAC)
		payload = {"message": BAC}
		requests.post(url, headers=headers, data=payload)

		now = dt.now()
		message = {"Date":"{0:%Y-%m-%d}".format(now),
				"Time":"{0:%H:%M:%S}".format(now),
				"message":"Alcohol is detected",
				"count":BAC}
		client.publish(topic, json.dumps(message)) #AWS IoTに送信(Publish)
		time.sleep(5)
		client.disconnect()

if_buf(Gas_buf)
