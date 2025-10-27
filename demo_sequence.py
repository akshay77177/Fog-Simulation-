import requests, time

API="http://localhost:8000/trigger"

def call(a,p):
    r=requests.post(API,json={"attack_type":a,"params":p}); print(r.text)

call("movement", {"count":6})
time.sleep(5)
call("resource", {"node_id":"iot_1","multiplier":4})
time.sleep(5)
call("inject", {"node_id":"attacker_demo","cluster":"cluster_1"})
time.sleep(5)
call("tamper", {"message":"fake_rekey_demo"})
