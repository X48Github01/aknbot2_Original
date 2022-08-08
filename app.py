import json
import time
from flask import Flask, request
from binance.client import Client
from binance.enums import *
import os
import requests

app = Flask(__name__)

API_KEY = str(os.environ['API_KEY'])
API_SECRET = str(os.environ['API_SECRET'])
TEST_NET = bool(str(os.environ['TEST_NET']))
LINE_TOKEN=str(os.environ['LINE_TOKEN'])
BOT_NAME=str(os.environ['BOT_NAME'])
FREEBALANCE=str(os.environ['FREEBALANCE'])
SECRET_KEY=str(os.environ['SECRET_KEY'])

client = Client(API_KEY,API_SECRET,testnet=TEST_NET)

#STATIC API for testnet
#API_KEY = '3ebbe4c386be6fd911894b3b0b72c6f2026959e47e74ed9aa0ff8f676a04a9c3'
#API_SECRET = '4b060561fddd153b5367614e8427bb5fd2a5b312f1dc2fff830278ddf36ed18a'
#client = Client(API_KEY,API_SECRET,testnet=True)


url = 'https://notify-api.line.me/api/notify'
headers = {'content-type':'application/x-www-form-urlencoded','Authorization':'Bearer '+LINE_TOKEN}
#msg = 'Hello LINE Notify'
#r = requests.post(url, headers=headers, data = {'message':msg})
#print (r.text)

#print(API_KEY)
#print(API_SECRET)

@app.route("/")
def hello_world():
    return "AKNB2"

@app.route("/webhook", methods=['POST'])
def webhook():
    data = json.loads(request.data)
    print("decoding data...")
    action = data['side']
    amount = data['amount']
    symbol = data['symbol']
    passphrase = data['passphrase']
    lev = data['leverage']
    #separate amount type
    fiat=0
    usdt=0
    percent=0
    
    
    #trim PERT from symbol
    if (symbol[len(symbol)-4:len(symbol)]) == "PERP":
        symbol=symbol[0:len(symbol)-4]

    
    COIN = symbol[0:len(symbol)-4] 
    
    if amount[0]=='@':
        fiat=float(amount[1:len(amount)])
        print("COIN>>",symbol, " : ",action," : amount=",fiat," : leverage=" , lev)
    if amount[0]=='$':
        usdt=float(amount[1:len(amount)])
        print("USDT>>",symbol, " : ",action," : amount=",usdt," : leverage=" , lev)
    if amount[0]=='%':
        percent= float(amount[1:len(amount)])
        print("Percent>>",symbol, " : ",action," : amount=",percent," : leverage=" , lev)
    
    print('amount=',amount)
    print('fiat=',fiat)
    print('USDT=',usdt)
    print('Percent=',percent)
        
    

    bid = 0
    ask = 0
    usdt = float(usdt)
    lev = int(lev)
    
    min_balance=0
    
    #check USDT Balance
    #balance_key='balance'
    balance_key='withdrawAvailable'    
    balance=float(client.futures_account_balance()[1][balance_key])
    
    #print(FREEBALANCE[0])
    if FREEBALANCE[0]=='$':
        min_balance=float(FREEBALANCE[1:len(FREEBALANCE)])
        print("FREEBALANCE=",min_balance)
    #Alertline if balance<min_balance
    if balance<min_balance:            
        msg ="BINANCE:\n" + "BOT       :" + BOT_NAME + "\n!!!WARNING!!!\nAccount Balance<"+ str(min_balance)+ " USDT"+"\nAccount Balance:"+ str(balance) + " USDT"
        r = requests.post(url, headers=headers, data = {'message':msg})
    
    bid = float(client.futures_orderbook_ticker(symbol =symbol)['bidPrice'])
    ask = float(client.futures_orderbook_ticker(symbol =symbol)['askPrice'])
        
    posiAmt = float(client.futures_position_information(symbol=symbol)[0]['positionAmt'])
    print("100% Position amount>>",float(client.futures_position_information(symbol=symbol)[0]['positionAmt']))
        
    #List of action OpenLong=BUY, OpenShort=SELL, StopLossLong, StopLossShort, CloseLong=LongTP, CloseShort=ShortTP, CloseLong, CloseShort, 
    #OpenLong/BUY    
    new_balance=0
    #if action == "OpenLong" and usdt>0:
    if action == "OpenLong" :
        qty_precision = 0
        for j in client.futures_exchange_info()['symbols']:
            if j['symbol'] == symbol:
                qty_precision = int(j['quantityPrecision'])
        #check if buy in @ or fiat
        if amount[0]=='@':            
            fiat=float(amount[1:len(amount)])
            Qty_buy=round(fiat,qty_precision)
            usdt=round(fiat*bid,qty_precision)
            print("BUY/LONG by @ amount=", fiat, " ", COIN, ">> USDT=",round(usdt,3))
        if amount[0]=='$':
            usdt=float(amount[1:len(amount)])
            Qty_buy = round(usdt/bid,qty_precision)
            print("BUY/LONG by USDT amount=", usdt, ">> COIN", round(usdt,30))
        print("CF>>", symbol,">>",action, ">>Qty=",Qty_buy, " ", COIN,">>USDT=", round(usdt,3))
        Qty_buy = round(Qty_buy,qty_precision)
        print('qty buy : ',Qty_buy)
        client.futures_change_leverage(symbol=symbol,leverage=lev) 
        print('leverage : ',lev)
        order_BUY = client.futures_create_order(symbol=symbol, side='BUY', type='MARKET', quantity=Qty_buy)        
        print(symbol," : BUY")        
        time.sleep(1)
        #get entry price to find margin value
        entryP=float(client.futures_position_information(symbol=symbol)[0]['entryPrice'])
        print("entryP=",entryP)
        margin=entryP*Qty_buy/lev
        #success openlong, push line notification        
        new_balance=float(client.futures_account_balance()[1][balance_key])
        print("Old Balance=",balance)
        print("New Balance=",new_balance)
        paid=balance-new_balance
        #paid=usdt/lev
        msg ="BINANCE:\n" + "BOT        :" + BOT_NAME + "\nCoin        :" + COIN + "/USDT" + "\nStatus     :" + action + "[BUY]" + "\nAmount  :" + str(Qty_buy) + " "+  COIN +"/"+str(usdt)+" USDT" + "\nPrice       :" + str(bid) + " USDT" + "\nLeverage:" + str(lev) +"\nMargin   :" + str(round(margin,2))+  " USDT"+ "\nPaid        :" + str(round(paid,2)) + " USDT"+ "\nBalance   :" + str(round(new_balance,2)) + " USDT"
        r = requests.post(url, headers=headers, data = {'message':msg})
        
    #OpenShort/SELL
    #if action == "OpenShort" and usdt > 0:        
    if action == "OpenShort" :                
        qty_precision = 0
        for j in client.futures_exchange_info()['symbols']:
            if j['symbol'] == symbol:
                qty_precision = int(j['quantityPrecision'])
        #check if sell in @ or fiat
        if amount[0]=='@':            
            fiat=float(amount[1:len(amount)])
            Qty_sell=round(fiat,qty_precision)
            usdt=round(fiat*ask,qty_precision)
            print("SELL/SHORT by @ amount=", fiat, " ", COIN, ">> USDT=",round(usdt,3))
        if amount[0]=='$':
            usdt=float(amount[1:len(amount)])
            Qty_sell = round(usdt/ask,qty_precision)
            print("SELL/SHORT by USDT amount=", usdt, ">> COIN", round(usdt,30))
        print("CF>>", symbol,">>", action, ">> Qty=", Qty_sell, " ", COIN,">>USDT=", round(usdt,3))
        Qty_sell = round(Qty_sell,qty_precision)
        print('qty sell : ',Qty_sell)
        client.futures_change_leverage(symbol=symbol,leverage=lev)
        print('leverage : ',lev)
        
        order_SELL = client.futures_create_order(symbol=symbol, side='SELL', type='MARKET', quantity=Qty_sell)
        print(symbol,": SELL")
        time.sleep(1)
        #get entry price to find margin value
        entryP=float(client.futures_position_information(symbol=symbol)[0]['entryPrice'])
        print("entryP=",entryP)
        margin=entryP*Qty_sell/lev
        #success openlong, push line notification        
        new_balance=float(client.futures_account_balance()[1][balance_key])
        print("Old Balance=",balance)
        print("New Balance=",new_balance)
        paid=balance-new_balance        #paid=usdt/lev
        #success openshort, push line notification        
#        msg ="BINANCE:\n" + "BOT        :" + BOT_NAME + "\nCoin        :" + COIN + "/USDT" + "\nStatus     :" + action + "[SHORT]" + "\nAmount  :" + str(Qty_sell) + " "+  COIN +"/"+str(usdt)+" USDT" + "\nPrice       :" + str(bid) + " USDT" + "\nLeverage:" + str(lev) + "\nPaid        :" + str(round(paid,3)) + " USDT" + "\nBalance     :" + str(round(new_balance,3)) + " USDT"
        msg ="BINANCE:\n" + "BOT        :" + BOT_NAME + "\nCoin        :" + COIN + "/USDT" + "\nStatus     :" + action + "[SHORT]" + "\nAmount  :" + str(Qty_sell) + " "+  COIN +"/"+str(usdt)+" USDT" + "\nPrice       :" + str(bid) + " USDT" + "\nLeverage:" + str(lev) +"\nMargin   :" + str(round(margin,2))+  " USDT"+ "\nPaid        :" + str(round(paid,2)) + " USDT"+ "\nBalance   :" + str(round(new_balance,2)) + " USDT"
        r = requests.post(url, headers=headers, data = {'message':msg})

        
    if action == "CloseLong":
        if posiAmt > 0.0 :
            qty_precision = 0
            for j in client.futures_exchange_info()['symbols']:
                if j['symbol'] == symbol:
                    qty_precision = int(j['quantityPrecision'])
            print("qty_precision",qty_precision)
            #check if sell in % or $
            if amount[0]=='%':            
                qty_close=round(percent*posiAmt/100,qty_precision)                
                usdt=round(qty_close*ask,qty_precision)                
                print("SELL/CloseLong by % amount=", qty_close, " ", COIN, ">> USDT=",round(usdt,3))
            if amount[0]=='$':
                usdt=float(amount[1:len(amount)])                
                qty_close = round(usdt/ask,qty_precision)                
                print("SELL/CloseLong by USDT amount=", usdt, ">> COIN", round(qty_close,3))
            print("CF>>", symbol,">>", action, ">> Qty=", qty_close, " ", COIN,">>USDT=", round(usdt,3))                    
            leverage = float(client.futures_position_information(symbol=symbol)[0]['leverage'])  
            entryP=float(client.futures_position_information(symbol=symbol)[0]['entryPrice'])*qty_close
            close_BUY = client.futures_create_order(symbol=symbol, side='SELL', type='MARKET', quantity=qty_close)            
            time.sleep(1)
            #success close sell, push line notification                    
            new_balance=float(client.futures_account_balance()[1][balance_key])
            profit = new_balance-balance
            margin=entryP/leverage
            ROI_val=100*profit/margin 
            ROI=0
            if ROI>=100:
                ROI=round(100-ROI_val,2)
            elif ROI<100:
                ROI=round(ROI_val-100,2)            
            print("Margin ROI%=",ROI)
            msg ="BINANCE:\n" + "BOT       :" + BOT_NAME + "\nCoin       :" + COIN + "/USDT" + "\nStatus    :" + action + "[SELL]" + "\nAmount  :" + str(qty_close) + " "+  COIN +"/"+str(round((qty_close*ask),3))+" USDT" + "\nPrice       :" + str(ask) + " USDT" + "\nLeverage:" + str(lev) + "\nReceive    :" + str(round(profit,2)) + " USDT" + "\nROI           :"+ str(round(ROI,2)) + "%"+"\nBalance   :" + str(round(new_balance,2)) + " USDT"
            r = requests.post(url, headers=headers, data = {'message':msg})
            print(symbol,": CloseLong")

    if action == "CloseShort":
        if posiAmt < 0.0 :
            qty_precision = 0
            for j in client.futures_exchange_info()['symbols']:
                if j['symbol'] == symbol:
                    qty_precision = int(j['quantityPrecision'])
            print("qty_precision",qty_precision)
            #check if buy in % or $
            if amount[0]=='%':            
                qty_close=round(percent*posiAmt/100,qty_precision)
                usdt=round(qty_close*bid,qty_precision)
                print("BUY/CloseShort by % amount=", qty_close, " ", COIN, ">> USDT=",round(usdt,3))
            if amount[0]=='$':
                usdt=float(amount[1:len(amount)])
                qty_close = -1*round(usdt/bid,qty_precision)
                print("BUY/CloseShort by USDT amount=", usdt, ">> COIN", round(qty_close,3))
            print("CF>>", symbol,">>",action, ">>Qty=",qty_close, " ", COIN,">>USDT=", round(usdt,3))
            leverage = float(client.futures_position_information(symbol=symbol)[0]['leverage'])              
            entryP=float(client.futures_position_information(symbol=symbol)[0]['entryPrice'])*qty_close
            close_SELL = client.futures_create_order(symbol=symbol, side='BUY', type='MARKET', quantity=qty_close*-1)                        
            time.sleep(1)    
            #success close sell, push line notification                    
            new_balance=float(client.futures_account_balance()[1][balance_key])
            profit = new_balance-balance
            margin=-1*entryP/leverage
            ROI_val=100*profit/margin 
            ROI=0
            if ROI>=100:
                ROI=round(100-ROI_val,2)
            elif ROI<100:
                ROI=round(ROI_val-100,2)            
            print("Margin ROI%=",ROI)            
            #success close buy, push line notification        
            #msg ="BINANCE:\n" + "BOT       :" + BOT_NAME + "\nCoin       :" + COIN + "/USDT" + "\nStatus    :" + action + "[BUY]" + "\nAmount  :" + str(qty_close*-1) + " "+  COIN +"/"+str(round((qty_close*ask*-1),3))+" USDT" + "\nPrice       :" + str(ask) + " USDT" + "\nLeverage:" + str(lev) + "\nReceive     :" + str(round((qty_close*ask*-1/lev),3)) + " USDT"+ "\nROI     :"+str(unRealizedProfit)+ " USDT"+"\nROI%    :"+str(ROI)
            #msg ="BINANCE:\n" + "BOT       :" + BOT_NAME + "\nCoin       :" + COIN + "/USDT" + "\nStatus    :" + action + "[BUY]" + "\nAmount  :" + str(qty_close*-1) + " "+  COIN +"/"+str(round((qty_close*bid*-1),3))+" USDT" + "\nPrice       :" + str(bid) + " USDT" + "\nLeverage:" + str(lev) + "\nReceive     :" + str(round((qty_close*bid*-1/lev),3)) + " USDT"+ "\nROI     :"+str(unRealizedProfit)+ " USDT"+"\nROI%    :"+str(ROI)
            msg ="BINANCE:\n" + "BOT       :" + BOT_NAME + "\nCoin       :" + COIN + "/USDT" + "\nStatus    :" + action + "[BUY]" + "\nAmount  :" + str(qty_close) + " "+  COIN +"/"+str(round((qty_close*bid),3))+" USDT" + "\nPrice       :" + str(bid) + " USDT" + "\nLeverage:" + str(lev) + "\nReceive    :" + str(round(profit,2)) + " USDT" + "\nROI           :"+ str(round(ROI,2)) + "%"+"\nBalance   :" + str(round(new_balance,2)) + " USDT"
            r = requests.post(url, headers=headers, data = {'message':msg})
            print(symbol,": CloseShort")
            
    if action == "test":
        print("TEST!")
        msg ="BINANCE:\n" + "BOT       :" + BOT_NAME + "\nTest.."
        r = requests.post(url, headers=headers, data = {'message':msg})        
    
    print("---------------------------------")

    return {
        "code" : "success",
        "message" : data
    }

if __name__ == '__main__':
    app.run(debug=True)
