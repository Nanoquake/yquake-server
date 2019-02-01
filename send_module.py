import requests, settings, time
from modules import nano

def send_discord(json_request):
    try:
        leaderboard_address = 'https://nanotournament.tk/webhooks/nanotournament/{}'.format(settings.server_name)
        r = requests.post(leaderboard_address, json = json_request, timeout = 3)
        print(r)
    except:
        print("Error discord")

def get_data(json_request):
    try:
        r = requests.post(settings.rai_node_address, data = json_request)
        return r
    except:
        message_list.append("Error - no connection to Nano node")
        return "Error"

def get_balance(account):
    json_request = '{"action" : "account_balance", "account" : "%s"}' % account
    r = get_data(json_request)
    if r == "Error":
        return "Error"
    resulting_data = r.json()
    balance = resulting_data['balance']
    return balance

def search_pending(account, index_pos, api_key):
    pending = nano.get_pending(str(account))
    print("Pending: {}".format(pending))

    while len(pending) > 0:
        print("Processing new blocks")
        pending = nano.get_pending(str(account))
        previous = nano.get_previous(str(account))

        try:
            if len(previous) == 0:
                print("Opening Account")
                hash, balance = nano.open_xrb(int(index_pos), account, settings.wallet_seed, api_key)
            else:
                hash, balance = nano.receive_xrb(int(index_pos), account, settings.wallet_seed, api_key)

        except:
            print("Error processing blocks")
    return 0

def rapid_process_send(block_hash, balance, account, api_key):
    hash, new_balance = nano.rapid_process(block_hash, balance, int(settings.index), account, settings.wallet_seed, api_key)
    return hash

def final_payout(firstPlace, secondPlace, thirdPlace, jointFirst, current_balance, api_key):
    #We need to calculate how much to give
    amount = current_balance
    print('{}'.format(amount))

    if thirdPlace != None:
        thirdAmount = int(amount) * 0.1
        send_xrb(thirdPlace, int(thirdAmount), api_key)

    if jointFirst !=None:
        jointAmount = int(get_balance(settings.source_account)) / 2
        print('{}'.format(jointAmount))
        send_xrb(firstPlace, int(jointAmount), api_key)
        jointAmount = int(get_balance(settings.source_account))
        print('{}'.format(jointAmount))
        send_xrb(jointFirst, int(jointAmount), api_key)

    else:
        if secondPlace != None:
            secondAmount = int(amount) * 0.3
            send_xrb(secondPlace, int(secondAmount), api_key)

        if firstPlace != None:
            firstAmount = get_balance(settings.source_account)
            print('{}'.format(amount))
            send_xrb(firstPlace, int(firstAmount), api_key)

def send_xrb(dest_address, amount, api_key):
    while int(get_balance(settings.source_account)) == 0:
        print("Error empty balance")
        search_pending(settings.source_account, api_key)
        time.sleep(2)

    x = 0
    while x < 4:
        #Find previous hash to allow for work to be generated
        #json_request = '{"action" : "account_info", "account" : "%s"}' % settings.source_account
        #r = get_data(json_request)
        #if r == "Error":
        #    return "Error"
        #resulting_data = r.json()
        #hash = resulting_data['frontier']

        #Generate work
        #json_request = '{"key" : "%s", "hash" : "%s"}' % (api_key, hash)
        #r = requests.post('http://178.62.11.37:5000/work', data = json_request)
        #resulting_data = r.json()
        #if 'work' in resulting_data:
        #    work = resulting_data['work']
        #    print(work)

        #    json_request = '{"action" : "send", "wallet" : "%s", "source" : "%s", "destination" : "%s", "amount" : "%d", "work" : "%s"}' % (settings.wallet, settings.source_account, dest_address, amount, work)
        #    try:
        #        r = get_data(json_request)
        #        if r == "Error":
        #            return "Error"
        #        resulting_data = r.json()
        #        print(resulting_data)
        #        if 'block' in resulting_data:
        #            print("Found Block")
        #            x = 5
        #            return (resulting_data['block'])
        #    except:
        #        pass
        return_block = nano.send_xrb(dest_address, amount, settings.source_account, int(settings.index), settings.wallet_seed, api_key)
        print("Return Block: {}".format(return_block))
        if 'hash' in return_block:
            x = 5

        x = x + 1

def send_faucet(dest_address, amount, api_key):
    x = 0
    while x < 4:

        return_block = nano.send_xrb(dest_address, amount, settings.faucet_account, 1, settings.wallet_seed, api_key)
        print("Return Block: {}".format(return_block))
        if 'hash' in return_block:
            x = 5

        x = x + 1
