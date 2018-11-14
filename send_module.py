import requests, settings

def get_data(json_request):
    try:
        r = requests.post(settings.rai_node_address, data = json_request)
        return r
    except:
        message_list.append("Error - no connection to Nano node")
        return "Error"

def get_balance(account):
    json_request = '{"action" : "account_balance", "account" : "%s"}' % settings.source_account
    r = get_data(json_request)
    if r == "Error":
        return "Error"
    resulting_data = r.json()
    balance = resulting_data['balance']
    return balance

def final_payout(firstPlace, secondPlace, thirdPlace, api_key):
    #We need to calculate how much to give
    amount = get_balance(settings.source_account)
    print('{}'.format(amount))

    if thirdPlace != None:
        thirdAmount = int(amount) * 0.1
        send_xrb(thirdPlace, int(thirdAmount), api_key)

    if secondPlace != None:
        secondAmount = int(amount) * 0.3
        send_xrb(secondPlace, int(secondAmount), api_key)

    if firstPlace != None:
        firstAmount = get_balance(settings.source_account)
        print('{}'.format(amount))
        send_xrb(firstPlace, int(firstAmount), api_key)

def send_xrb(dest_address, amount, api_key):
    x = 0
    while x < 4:
        #Find previous hash to allow for work to be generated
        json_request = '{"action" : "account_info", "account" : "%s"}' % settings.source_account
        r = get_data(json_request)
        if r == "Error":
            return "Error"
        resulting_data = r.json()
        hash = resulting_data['frontier']

        #Generate work
        json_request = '{"key" : "%s", "hash" : "%s"}' % (api_key, hash)
        r = requests.post('http://178.62.11.37:5000/work', data = json_request)
        resulting_data = r.json()
        work = resulting_data['work']
        print(work)

        json_request = '{"action" : "send", "wallet" : "%s", "source" : "%s", "destination" : "%s", "amount" : "%d", "work" : "%s"}' % (settings.wallet, settings.source_account, dest_address, amount, work)
        try:
            r = get_data(json_request)
            if r == "Error":
                return "Error"
            resulting_data = r.json()
            print(resulting_data)
            if 'block' in resulting_data:
                print("Found Block")
                x = 5
                return (resulting_data['block'])
        except:
            pass

        x = x + 1
