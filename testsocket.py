#!/usr/bin/env python3

import socket
import time
import requests, argparse, random

HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
PORT = 65432        # Port to listen on (non-privileged ports are > 1023)

parser = argparse.ArgumentParser()
parser.add_argument("--rai_node_uri", help='rai_nodes uri, usually 127.0.0.1', default='127.0.0.1')
parser.add_argument("--rai_node_port", help='rai_node port, usually 7076', default='7076')
parser.add_argument("--internal_port", help='internal port which nginx proxys', default='5000')

args = parser.parse_args()

raw = 1000000000000000000000000000000.0
api_key = '396ECD96DAF6CA1B4E711494D046F8B7'
rai_node_address = 'http://%s:%s' % (args.rai_node_uri, args.rai_node_port)
source_account = 'xrb_3j8xtnbqyn5rkueosfr7dbf9sth8ta16n3wpd51oogrjmsy4oofagw6jcmmw'
wallet = 'D5CCCD3280E3184D6C42036551B1C1239841950D58E36479CB7F0572D0243A24'

def send_xrb(dest_address):
    json_request = '{"action" : "account_info", "account" : "%s"}' % source_account
    r = requests.post(rai_node_address, data = json_request)
    resulting_data = r.json()
    hash = resulting_data['frontier']
    amount = int(1000000000000000000000000000)
    print('{}'.format(amount))
    json_request = '{"key" : "%s", "hash" : "%s"}' % (api_key, hash)
    r = requests.post('http://178.62.11.37:5000/work', data = json_request)
    resulting_data = r.json()
    work = resulting_data['work']
    print(work)

    json_request = '{"action" : "send", "wallet" : "%s", "source" : "%s", "destination" : "%s", "amount" : "%d", "work" : "%s"}' % (wallet, source_account, dest_address, amount, work)
    r = requests.post(rai_node_address, data = json_request)
    resulting_data = r.json()
    print(resulting_data)
    amount_Nano = float(amount) / raw
    return (resulting_data['block'], (amount_Nano))

while True:
  try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
      s.bind((HOST, PORT))
      s.listen()
      conn, addr = s.accept()
      with conn:
          print('Connected by', addr)
          while True:
              data = conn.recv(1024)
              if not data:
                  break
              print("{} {}".format(time.strftime("%d/%m/%Y %H:%M:%S"),data))
              split_data = data.decode('utf8').split(",")
              if split_data[0] == "selfkill":
                  print("{} killed themselves, no payout".format(split_data[1]))
              elif split_data[0] == "kill":
                  print("{} killed, payout".format(split_data[1]))
                  #send
                  dest_address = "xrb_" + split_data[1]
                  send_xrb(dest_address)
                  print("Sent to {}".format(dest_address))

              data = None
              #conn.sendall(data)
  except KeyboardInterrupt:
    print("\nCtrl-C detected, canceled by user\n")
    break
