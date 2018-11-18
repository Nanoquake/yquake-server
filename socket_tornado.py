# TAKEN FROM: http://alexapps.net/python-tornado-simple-tcp-server

import socket
import tornado.gen
import tornado.ioloop
import tornado.iostream
import tornado.tcpserver
import time, requests, argparse, random
from operator import itemgetter
import settings
from send_module import send_xrb
from send_module import final_payout
from decimal import Decimal

from redis import Redis
from rq import Queue

q = Queue(connection=Redis())

HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
PORT = 65432        # Port to listen on (non-privileged ports are > 1023)

parser = argparse.ArgumentParser()
parser.add_argument("--rai_node_uri", help='rai_nodes uri, usually 127.0.0.1', default='127.0.0.1')
parser.add_argument("--rai_node_port", help='rai_node port, usually 7076', default='7076')
parser.add_argument("--internal_port", help='internal port which nginx proxys', default='5000')
parser.add_argument("--dpow_key", help='dPoW key')

args = parser.parse_args()

raw = 1000000000000000000000000000000.0
api_key = args.dpow_key
rai_node_address = 'http://%s:%s' % (args.rai_node_uri, args.rai_node_port)
frag_limit = 20
game_time = [-1]

game_players = []
paid_in_players = []
message_list = []
name_address = {}
account_count = 0
server_balance = 0
scoreboard = {}

def get_data(json_request):
    try:
        r = requests.post(rai_node_address, data = json_request)
        return r
    except:
        message_list.append("Error - no connection to Nano node")
        return "Error"

def get_frontier(account):
    json_request = '{"action" : "account_info", "account" : "%s"}' % settings.source_account
    r = get_data(json_request)
    if r == "Error":
        return "Error"
    resulting_data = r.json()
    frontier = resulting_data['frontier']
    return frontier

def get_balance(account):
    json_request = '{"action" : "account_balance", "account" : "%s"}' % settings.source_account
    r = get_data(json_request)
    if r == "Error":
        return "Error"
    resulting_data = r.json()
    balance = resulting_data['balance']
    return balance

def get_account_count(account):
    json_request = '{"action" : "account_block_count", "account" : "%s"}' % settings.source_account
    r = get_data(json_request)
    if r == "Error":
        return "Error"
    resulting_data = r.json()
    account_count = resulting_data['block_count']
    return account_count

def get_account_history(account, count):
    json_request = '{"action" : "account_history", "account" : "%s", "count" : "%d"}' % (settings.source_account, count)
    r = get_data(json_request)
    if r == "Error":
        return "Error"
    resulting_data = r.json()
    account_history = resulting_data['history']
    return account_history

def kill_payout(dest_address):
    #We need to calculate how much to give
    raw_balance = get_balance(settings.source_account)
    print("Raw {}".format(raw_balance))
    amount = int( (int(raw_balance) * 0.75) / (len(paid_in_players) * frag_limit) )
#    amount = int(1000000000000000000000000000)
    print('Amount {}'.format(amount))
    #Use send xrb function to send
    #_thread.start_new_thread(send_xrb, (dest_address, amount,))
    #send_xrb(dest_address, amount)
    result = q.enqueue(send_xrb, dest_address, int(amount), api_key)
    print("kill payout added to queue")
def get_player_address(client_address):
    player_address = "xrb_" + client_address
#    print("{} {} {}".format(player_address, len(player_address), player_address[64:]))
    if len(player_address) > 64:
        player_address = player_address[:-1]
 #   print(player_address)
    return player_address

class SimpleTcpClient(object):
    client_id = 0

    def __init__(self, stream):
        super().__init__()
        SimpleTcpClient.client_id += 1
        self.id = SimpleTcpClient.client_id
        self.stream = stream

        self.stream.socket.setsockopt(
            socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.stream.socket.setsockopt(
            socket.IPPROTO_TCP, socket.SO_KEEPALIVE, 1)
        self.stream.set_close_callback(self.on_disconnect)


    @tornado.gen.coroutine
    def on_disconnect(self):
        self.log("disconnected")
        yield []

    @tornado.gen.coroutine
    def dispatch_client(self):
        try:
            while True:
                line = yield self.stream.read_until(b'\n')
                try:
                    self.log('got |%s|' % line.decode('utf-8').strip())
                    print("{} {}".format(time.strftime("%d/%m/%Y %H:%M:%S"),line))
                    split_data = line.rstrip().decode('utf8').split(",")
                except:
                     pass

                if split_data[0] == "selfkill":
                    print("{} killed themselves, no payout".format(split_data[1]))
                elif split_data[0] == "kill":
                    print("{} killed, payout".format(split_data[1]))
                    if split_data[1] == 'noaddress':
                        print("Error - noaddress kill - igonored")
                    else:
                        #send
                        dest_address = get_player_address(split_data[1])
                        vict_address = get_player_address(split_data[2])
                        if dest_address in paid_in_players:
                            if not dest_address in scoreboard:
                                scoreboard[dest_address] = 1
                            else:
                                scoreboard[dest_address] += 1
                            print("kill 1")
                            kill_payout(dest_address)
                            print("Sent to {}".format(dest_address))
                        json_request = '{"game" : "quake2", "action": "kill", "attacker": {"name" : "%s", "address" : "%s"}, "victim": {"name" : "%s", "address" : "%s"}}' % (split_data[3], dest_address, split_data[4], vict_address)
                        #r = requests.post('https://nanotournament.tk/webhooks/nanotournament', json = json_request)

                elif split_data[0] == "disconnect":
                    print("{} disconnected".format(split_data[1]))
                    player_address = get_player_address(split_data[1])
                    json_request = '{"game" : "quake2", "players" : "%d", "action": "disconnect", "player" : {"name" : "%s", "address": "%s"}}' % ((len(game_players)-1), split_data[2], player_address)
                    #r = requests.post('https://nanotournament.tk/webhooks/nanotournament', json = json_request)
                    if player_address in game_players:
                        game_players.remove(player_address)
                    if player_address in paid_in_players:
                        paid_in_players.remove(player_address)

                elif split_data[0] == "connect":
                    print("{} connected".format(split_data[1]))
                    if game_time[0] == -1:
                        game_time[0] = time.time() + 600
                    player_address = get_player_address(split_data[1])
                    if player_address not in game_players:
                        game_players.append(player_address)
                        json_request = '{"game" : "quake2", "players" : "%d", "action": "connect", "player" : {"name" : "%s", "address": "%s"}}' % (len(game_players), split_data[2], player_address)
                        print(json_request)
                        #r = requests.post('https://nanotournament.tk/webhooks/nanotournament', json = json_request)
#                       print(r.text)
                        name_address[player_address] = split_data[2]

                elif split_data[0] == "roundend":
                    print("{} round ended".format(split_data[1]))
                    json_request = '{"game" : "quake2", "players" : "%d", "action": "round_end"}' % (len(game_players))
                    #r = requests.post('https://nanotournament.tk/webhooks/nanotournament', json = json_request)
                    #Decide winner and payout TODO
                    winner = None
                    secondPlace = None
                    thirdPlace = None
                    jointFirst = None
                    print(scoreboard)
#                    for key, value in sorted(scoreboard.iteritems(), key=lambda (k,v): (v,k)):
                    for key, value in sorted(scoreboard.items(), key = itemgetter(1), reverse = True):
                        print("{}: {}".format(key, value))
                        if winner == None:
                            winner = key
                            message_list.append("1st place is {}".format(name_address[winner]))
                        elif secondPlace == None:
                            secondPlace = key
                            if value == scoreboard[winner]:
                                jointFirst = key
                                message_list.append("\nJoint 1st place is {}".format(name_address[secondPlace]))
                            else:
                                message_list.append("\n2nd place is {}".format(name_address[secondPlace]))
                        elif thirdPlace == None:
                            thirdPlace = key
                            message_list.append("\n3nd place is {}".format(name_address[thirdPlace]))

                    result = q.enqueue(final_payout, winner, secondPlace, thirdPlace, jointFirst,  api_key)

                    #Here if there have been no kills then we should refund the players
                    if winner == None:
                        num_paid_in = len(paid_in_players)
                        if num_paid_in == 1:
                            amount = get_balance(settings.source_account)
                            #_thread.start_new_thread(send_xrb, (dest_address, int(amount),))
                            q.enqueue(send_xrb, paid_in_players[0], int(amount), api_key)

                            #send_xrb(paid_in_players[0], int(amount))
                            print('Refund :{}'.format(amount))
                        elif num_paid_in > 1:
                           #We need to calculate how much to give
                            message_list.append("No Winners so refunding players")
                            amount = int(get_balance(settings.source_account)) / num_paid_in

                            for players in paid_in_players:
                                #Use send xrb function to send
                                #_thread.start_new_thread(send_xrb, (dest_address, int(amount),))
                                result = q.enqueue(send_xrb, players, int(amount), api_key)

                            #    send_xrb(players, int(amount))
                        else:
                            message_list.append("No players paid in, rolling over funds")

                    #Reset game_time
                    game_time[0] = time.time() + 600
                    #Clear list
                    scoreboard.clear()
                    game_players.clear()
                    paid_in_players.clear()
                    name_address.clear()


                elif split_data[0] == "poll":
                    global server_balance
                    return_string = " "
                    #print(message_list)
                    for messages in message_list:
                        return_string += messages
                        return_string += '\n'
                    return_string += "Paid in: "
                    for player in paid_in_players:
                        return_string += "{} ".format(name_address[player])

                    not_paid_in = list(set(game_players)-set(paid_in_players))
                    return_string += "\nNot paid in: "
                    for player in not_paid_in:
                        return_string += "{} ".format(name_address[player])

                    print(server_balance)
                    return_string += "   Server Balance: {:.3} Nano".format(Decimal(server_balance))
                    message_list.clear()
                    print("Return String: {} {}".format(return_string, len(return_string)))
                    yield self.stream.write(return_string.encode('ascii'))

                elif split_data[0] == "new_round":
                    print("Round start")

        except tornado.iostream.StreamClosedError:
            pass

    @tornado.gen.coroutine
    def on_connect(self):
        raddr = 'closed'
        try:
            raddr = '%s:%d' % self.stream.socket.getpeername()
        except Exception:
            pass
        self.log('new, %s' % raddr)

        yield self.dispatch_client()

    def log(self, msg, *args, **kwargs):
        print('[connection %d] %s' % (self.id, msg.format(*args, **kwargs)))


class SimpleTcpServer(tornado.tcpserver.TCPServer):

    @tornado.gen.coroutine
    def handle_stream(self, stream, address):
        """
        Called for each new connection, stream.socket is
        a reference to socket object
        """
        connection = SimpleTcpClient(stream)
        yield connection.on_connect()

@tornado.gen.coroutine
def check_account():
    print(game_players)
    print(paid_in_players)

    global account_count
    global server_balance
    print("Update {}".format(time.time()))
    current_count = get_account_count(settings.source_account)
    if(int(current_count) > int(account_count)):
        count = int(current_count) - int(account_count)
        print("Count: {}, {},  {}".format(current_count, account_count,  count))
        complete_history = get_account_history(settings.source_account, count)
        for blocks in complete_history:
            print(blocks)
            if blocks['type'] == 'receive':
                print(blocks)
                #0.01
                if blocks['account'] in game_players and blocks['account'] in paid_in_players:
                    print("Double Pay - return to sender {}".format(blocks['account']))
                    #_thread.start_new_thread(send_xrb, (dest_address, int(amount),))
                    amount = int(blocks['amount'])
                    result = q.enqueue(send_xrb, blocks['account'], int(amount), api_key)
                    #send_xrb(blocks['account'], int(blocks['amount']))
                    message_list.append("{} tried to double pay".format(name_address[blocks['account']]))


                elif blocks['account'] in game_players and int(blocks['amount']) >= 10000000000000000000000000000 and blocks['account'] not in paid_in_players:
                    print("{} has paid in".format(blocks['account']))
                    paid_in_players.append(blocks['account'])
                    message_list.append("{} has paid in".format(blocks['account']))
                    json_request = '{"game" : "quake2", "player" : "%s", "action": "pay_in", "address" : "%s"}' % (name_address[blocks['account']], blocks['account'])
                    #r = requests.post('https://nanotournament.tk/webhooks/nanotournament', json = json_request)

        account_count = current_count
    server_balance = Decimal(get_balance(settings.source_account)) / Decimal(raw)


def main():
    #ON BOOT WE NEED TO GET FRONTIER
    starting_frontier = get_frontier(settings.source_account)
    print("Starting block is {}, {}".format(starting_frontier, account_count))

    # tcp server
    server = SimpleTcpServer()
    server.listen(PORT, HOST)
    print("Listening on %s:%d..." % (HOST, PORT))

    #
    pc = tornado.ioloop.PeriodicCallback(check_account, 10000)
    pc.start()

    # infinite loop
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    account_count = get_account_count(settings.source_account)

    main()
