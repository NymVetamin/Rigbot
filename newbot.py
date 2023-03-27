import requests
import time
import schedule
from threading import Thread
import json
import telebot
import sqlite3
from telebot import types
import bot_settings
import os.path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from webdriver_manager.core.utils import ChromeType


os.chdir(bot_settings.base_dir)


def get_json(message, rig, qdev = False):
	try:
		rigstat = requests.get(f'http://{rig}/api/v1/status', timeout = 4)
	except Exception:
		bot.send_message(message.chat.id,f'⚠️Error getting info with {rig}' ,parse_mode='html')
		return False
	rigstat_json = json.loads(rigstat.text)
	num_of_dev = len(rigstat_json['miner']['devices'])
	if qdev:
		return num_of_dev
	else:
		return rigstat_json


def h_to_mh(hashrate: float):
	hashrate=hashrate/1000000
	return(round(hashrate, 2))

def norm_info(info):
	info = info.replace(' NVIDIA GeForce', '')
	return info

def get_wallet(message, for_scheduler = False):
	wallet = ''
	for i in bot_settings.Rig_addr:
		rigstat_json = get_json(message, i)
		if not rigstat_json:
			if i == bot_settings.Rig_addr[-1]:
				bot.send_message(message.chat.id,f'Error getting wallet address',parse_mode='html')
				return False
			continue
		user = rigstat_json['stratum']['user']
		dot_index = user.find('.')
		user = user[:dot_index]
		if wallet.find(user) == -1:
			wallet += '\n' + user
	if not for_scheduler:
		bot.send_message(message.chat.id,f'Your Wallet is: <b>{wallet}</b>',parse_mode='html')
	return wallet

def average_income_calc(message, wallet, count = 0):
	if not wallet:
		return False
	global avg_income_list
	global avg_income
	chrome_options = Options()
	chrome_options.add_argument('--headless')
	chrome_options.add_argument('--no-sandbox')
	chrome_options.add_argument('--disable-dev-shm-usage')
	try:
		browser = webdriver.Chrome(service = Service(ChromeDriverManager(chrome_type = ChromeType.CHROMIUM).install()), options = chrome_options)
		browser.get(f'https://etc.2miners.com/ru/account/{wallet}')
		time.sleep(5)
		pay_for_day_elem = browser.find_element(By.XPATH, '//*[@id="miner-info"]/div/div[3]/div/div/div[2]/div[1]/div[2]/span[1]')
		pay_for_day = pay_for_day_elem.text
		browser.quit()
		indx = pay_for_day.find(' ')
		pay_for_day = float(pay_for_day[indx+1:])
	except Exception:
		if count < 5:
			count += 1
			time.sleep(20)
			average_income_calc(message, wallet, count)
		else:
			bot.send_message(message.chat.id,'Error getting info from 2Miners', parse_mode='html')
		return
	if avg_income_list[0] == 0:
		for i in range(len(avg_income_list)):
			avg_income_list[i] = pay_for_day
	avg_income_list.insert(0, pay_for_day)
	avg_income_list.pop()
	avg_income = sum(avg_income_list)/len(avg_income_list)
	return pay_for_day

def check_gminer(message, count = 0):
	if not param_update(message):
		return
	git = "https://github.com/develsoftware/GMinerRelease/releases"
	curr_release = 0
	chrome_options = Options()
	chrome_options.add_argument('--headless')
	chrome_options.add_argument('--no-sandbox')
	chrome_options.add_argument('--disable-dev-shm-usage')
	try:
		browser = webdriver.Chrome(service=Service(ChromeDriverManager(chrome_type = ChromeType.CHROMIUM).install()), options = chrome_options)
	except Exception:
		bot.send_message(message.chat.id,f'Error install driver',parse_mode='html')
		return
	for i in bot_settings.Rig_addr:
		try:
			browser.get(f'http://{i}')
			time.sleep(3)
			curr_release_elem = browser.find_element(By.ID, 'miner_name')
			curr_release_rig = curr_release_elem.text
		except Exception:
			bot.send_message(message.chat.id,f'Error getting info from RIG {i}',parse_mode = 'html')
			if i == bot_settings.Rig_addr[-1]:
				return
			continue
		for j in curr_release_rig:
			if not j.isdecimal():
				curr_release_rig = curr_release_rig.replace(j, '')
		if int(curr_release_rig) > curr_release:
			curr_release = int(curr_release_rig)
	try:
		browser.get(git)
		time.sleep(3)
		release_elem = browser.find_element(By.TAG_NAME, 'h1')
		release = release_elem.text
		browser.quit()
	except Exception:
		if count < 5:
			count+=1
			time.sleep(30)
			check_gminer(message, count)
		else:
			bot.send_message(message.chat.id,'Error getting info from GitHub',parse_mode='html')
		return
	for i in release:
		if not i.isdecimal():
			release = release.replace(i, '')
	if int(release) > curr_release:
		release = f'{release[:1]}.{release[1:]}'
		bot.send_message(message.chat.id,f'New Gminer Release: <b>{release}</b>',parse_mode='html')
	return release



def smart_status(message, checker = False):
	if not param_update(message):
		return
	hashrate = 0
	card = [0] * len(bot_settings.Rig_addr)
	stat_mess = ''
	for i in range(len(bot_settings.Rig_addr)):
		rigstat_json = get_json(message, bot_settings.Rig_addr[i])
		if not rigstat_json:
			stat_mess += f'\n⛏<b>RIG{i+1}</b> probably offline'
			continue
		num_of_dev = get_json(message, bot_settings.Rig_addr[i], True)
		if not num_of_dev:
			stat_mess += f'\n⛏<b>RIG{i+1}</b> probably offline'
			continue
		card[i] = [0] * num_of_dev
		for j in range(num_of_dev):
			info = rigstat_json['miner']['devices'][j]['info']
			temp = rigstat_json['miner']['devices'][j]['temperature']
			mem_temp = rigstat_json['miner']['devices'][j]['memory_temperature']
			hashrate += rigstat_json['miner']['devices'][j]['hashrate']
			power = rigstat_json['miner']['devices'][j]['power']
			if temp > bot_settings.crit_temp:
				stat_mess += f'\n⛏RIG{i+1} Card{j+1} temp: 🌡<b>{temp}</b>C'
			if mem_temp > bot_settings.crit_mem_temp:
				stat_mess += f'\n⛏RIG{i+1} Card{j+1} memory temp: 🌡<b>{mem_temp}</b>C'
			if power > bot_settings.crit_power:
				stat_mess += f'\n⛏RIG{i+1} Card{j+1} power: 🔌<b>{power}</b>W'
		if stat_mess !='':
			stat_mess += '\n'
	hashrate = h_to_mh(hashrate)
	if hashrate < bot_settings.common_hr * 0.93:
		stat_mess += f'\nTotal hashrate: <b>{hashrate}</b>MH/s, normal hashrate is: <b>{bot_settings.common_hr}</b>MH/s'
	if stat_mess == '':
		stat_mess = '✅<b>OK</b>'
		status = True
	else:
		stat_mess = f'🆘<b>BAD</b> {stat_mess}'
		status = False
	if checker == True and status == True:
		return status
	bot.send_message(message.chat.id, stat_mess, parse_mode='html')
	return status


#Hashrate rig by rig calculating
def hashrate(message):
	if not param_update(message):
		return
	hashrate_text=''
	for i in bot_settings.Rig_addr:
		hashrate= 0
		rigstat_json = get_json(message, i)
		if not rigstat_json:
			continue
		num_of_dev = get_json(message, i, True)
		if not num_of_dev:
			continue
		for j in range(num_of_dev):
			hashrate += rigstat_json['miner']['devices'][j]['hashrate']
		shares = rigstat_json['stratum']['shares_per_minute']
		hashrate_text += f'⛏<b>RIG {i}:</b>\nHashrate: <b>{str(h_to_mh(hashrate))}</b>MH/s\nShares/min: <b>{shares}</b>\n'
	bot.send_message(message.chat.id,hashrate_text,parse_mode='html')

#Total hashrate calculating
def total_hashrate(message):
	if not param_update(message):
		return
	hashrate,shares = 0,0
	for i in bot_settings.Rig_addr:
		rigstat_json = get_json(message, i)
		if not rigstat_json:
			continue
		num_of_dev = get_json(message, i, True)
		if not num_of_dev:
			continue
		for j in range(num_of_dev):
			hashrate += rigstat_json['miner']['devices'][j]['hashrate']
		shares += rigstat_json['stratum']['shares_per_minute']
	hashrate = f'Total hashrate: <b>{h_to_mh(hashrate)}</b>MH/s\nTotal shares/min: <b>{shares}</b>'
	bot.send_message(message.chat.id,hashrate,parse_mode='html')

#Total info calculating
def total_info(message):
	if not param_update(message):
		return
	totalinfo=''
	for i in bot_settings.Rig_addr:
		rigstat_json = get_json(message, i)
		if not rigstat_json:
			continue
		num_of_dev = get_json(message, i, True)
		if not num_of_dev:
			continue
		card=[0] * num_of_dev
		totalinfo += f'⛏<b>RIG {i}</b>:\n\n'
		for j in range(num_of_dev):
			info = str(rigstat_json['miner']['devices'][j]['info'])
			info = norm_info(info)
			temp = str(rigstat_json['miner']['devices'][j]['temperature'])
			mem_temp = str(rigstat_json['miner']['devices'][j]['memory_temperature'])
			if mem_temp != '0':
				temp +=f'/{mem_temp}'
			hashrate = str(h_to_mh(rigstat_json['miner']['devices'][j]['hashrate']))
			power = str(rigstat_json['miner']['devices'][j]['power'])
			totalinfo += f'{info} 🌡<b>{temp}</b>C <b>{hashrate}</b>MH/s 🔌<b>{power}</b>W\n'
		totalinfo += '\n'
	bot.send_message(message.chat.id, totalinfo, parse_mode='html')


def difficulty(message):
	bot.send_message(message.chat.id, 'Working...', parse_mode = 'html')
	chrome_options = Options()
	chrome_options.add_argument('--headless')
	chrome_options.add_argument('--no-sandbox')
	chrome_options.add_argument('--disable-dev-shm-usage')
	try:
		browser = webdriver.Chrome(service=Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()), options=chrome_options)
		browser.get('https://2miners.com/etc-stats/')
		time.sleep(3)
		difficulty_elem = browser.find_element(By.XPATH, '/html/body/div[1]/div/div/div[1]/div[6]/div/div/div[2]/span/span')
		web_hashrate_elem = browser.find_element(By.XPATH, '/html/body/div[1]/div/div/div[1]/div[5]/div/div/div[2]/span')
		difficulty = difficulty_elem.text
		web_hashrate = web_hashrate_elem.text
		browser.quit()
	except Exception:
		bot.send_message(message.chat.id, 'Error getting info from source', parse_mode = 'html')
		return
	mess = f'Difficulty: <b>{difficulty}</b>\nWeb-hashrate: <b>{web_hashrate}</b>'
	bot.send_message(message.chat.id, mess, parse_mode = 'html')


def settings_buttons(message, mess):
	markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width = 2)
	common_hr_but = types.KeyboardButton('Common Hashrate')
	crit_temp_but = types.KeyboardButton('Crit temp')
	crit_mem_temp_but = types.KeyboardButton('Crit memory temp')
	crit_power_but = types.KeyboardButton('Crit power')
	rigs_but = types.KeyboardButton('Rigs list')
	back = types.KeyboardButton('↩️Back')
	markup.add(common_hr_but, crit_temp_but, crit_mem_temp_but, crit_power_but, rigs_but, back)
	bot.send_message(message.chat.id, mess, reply_markup = markup, parse_mode = 'html')




def settings_st3(message, column):
	if message.text == '↩️Back':
		settings_st1(message)
		return
	new_value = message.text.replace(' ', '')
	if column in ['Common Hashrate', 'Crit temp', 'Crit memory temp', 'Crit power'] and not new_value.isnumeric():
		bot.send_message(message.chat.id, 'Only numeric values! repeat: ',parse_mode = 'html')
		settings_st1(message)
		return
	base = sqlite3.connect('base.db')
	cur = base.cursor()
	bot.send_message(message.chat.id, 'ok',parse_mode = 'html')
	if column == 'Common Hashrate':
		column = 'common_hr'
	elif column == 'Crit temp':
		column = 'crit_temp'
	elif column == 'Crit memory temp':
		column = 'crit_mem_temp'
	elif column == 'Crit power':
		column = 'crit_power'
	elif column == 'Rigs list':
		column = 'rigs'
	cur_value = cur.execute(f'SELECT {column} FROM settings WHERE id == ?', (message.chat.id, )).fetchone()
	if cur_value == None and column != 'rigs':
		cur.execute(f'INSERT INTO settings(id,{column}) VALUES(?,?)', (message.chat.id, new_value))
	elif cur_value == None and column == 'rigs':
		cur.execute(f'INSERT INTO settings(id,{column}) VALUES(?,?)', (message.chat.id, new_value))
	elif cur_value != None and column == 'rigs':
		cur.execute(f'UPDATE settings SET {column} == ? WHERE id == ?', (new_value, message.chat.id))
	else:
		cur.execute(f'UPDATE settings SET {column} == ? WHERE id == ?', (new_value, message.chat.id))
	base.commit()
	base.close()
	settings_st1(message)

def settings_st2(message):
	if message.text == '↩️Back':
		buttons(message)
		return
	elif message.text in ['Common Hashrate', 'Crit temp', 'Crit memory temp', 'Crit power', 'Rigs list']:
		if message.text == 'Rigs list':
			bot.send_message(message.chat.id, 'Enter the addresses and ports of the rigs separated by commas, for example: 192.168.1.2:20030,192.168.1.3:20030',parse_mode = 'html')
		markup = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = 2)
		back = types.KeyboardButton('↩️Back')
		markup.add(back)
		bot.send_message(message.chat.id, f'New value for {message.text}:', reply_markup = markup, parse_mode = 'html')
		bot.register_next_step_handler(message, settings_st3, message.text)
	else:
		bot.send_message(message.chat.id, 'Repeat your choise: ',parse_mode = 'html')
		settings_st1(message)


def settings_st1(message):
	mess = ''
	base = sqlite3.connect('base.db')
	cur = base.cursor()
	current_settings = cur.execute('SELECT * FROM settings WHERE id = ?', (message.chat.id, )).fetchall()
	base.close()
	if current_settings == []:
		mess += 'Settings are not set'
	else:
		mess += '<i><u>Current settings:</u></i>\n'
		mess += f'Common Hashrate: <b>{current_settings[0][1]}</b>\nCrit temp: <b>{current_settings[0][2]}</b>\nCrit memory temp: <b>{current_settings[0][3]}</b>\nCrit power: <b>{current_settings[0][4]}</b>\n'
		rigs_list = current_settings[0][5].replace(",", "\n")
		mess += f'Rigs list:\n<b>{rigs_list}</b>'
	settings_buttons(message, mess)
	bot.register_next_step_handler(message, settings_st2)


def param_update(message):
	base = sqlite3.connect('base.db')
	cur = base.cursor()
	current_settings = cur.execute('SELECT * FROM settings WHERE id = ?', (message.chat.id, )).fetchall()
	base.close()
	for count, i in enumerate(current_settings[0]):
		if count == 1:
			param = 'Common Hashrate'
		elif count == 2:
			param = 'Crit temp'
		elif count == 3:
			param = 'Crit memory temp'
		elif count == 4:
			param = 'Crit power'
		elif count == 5:
			param = 'Rigs list'
		if i == None:
			bot.send_message(message.chat.id,f'{param} is not set', parse_mode = 'html')
			return False
	bot_settings.common_hr = current_settings[0][1]
	bot_settings.crit_temp = current_settings[0][2]
	bot_settings.crit_mem_temp = current_settings[0][3]
	bot_settings.crit_power = current_settings[0][4]
	bot_settings.Rig_addr = current_settings[0][5].split(',')
	return True


def ip_change_st3(message):
	if message.text == '↩️Back':
		buttons(message)
		return
	elif message.text == 'OK':
		bot.send_message(message.chat.id, 'Confirmed!', parse_mode = 'html')
		buttons(message)
	elif message.text == 'Change':
		ip_change_st2(message)
	else:
		bot.send_message(message.chat.id, f'Repeat your request', parse_mode = 'html')
		bot.register_next_step_handler(message, ip_change_st2)

def ip_change_st2(message):
	if message.text in ['↩️Back', 'Cancel']:
		buttons(message)
		return
	elif message.text in ['Yes', 'Change']:
		bot.send_message(message.chat.id, 'Working... it may take 1 minute...', parse_mode = 'html', reply_markup = types.ReplyKeyboardRemove())
		chrome_options = Options()
		chrome_options.add_argument('--headless')
		chrome_options.add_argument('--no-sandbox')
		chrome_options.add_argument('--disable-dev-shm-usage')
		browser = webdriver.Chrome(service = Service(ChromeDriverManager(chrome_type = ChromeType.CHROMIUM).install()), options = chrome_options)
		try:
			browser.get('http://admin:admin@192.168.1.1')
		except Exception:
			bot.send_message(message.chat.id, 'Error connecting to host', parse_mode = 'html')
			browser.quit()
			return
		WebDriverWait(browser, 10).until(ec.visibility_of_element_located((By.XPATH, '//*[@id="page_frame"]/div[2]/div/ul/li[2]/a'))).click()
		WebDriverWait(browser, 10).until(ec.visibility_of_element_located((By.XPATH, '//*[@id="page"]/div[2]/form/div/div[2]/table/tbody/tr[1]'))).click()
		# WebDriverWait(browser, 10).until(ec.visibility_of_element_located((By.XPATH, '/html/body/div[3]/form/div[2]/div[3]/div/div[2]/button'))).click()
		WebDriverWait(browser, 10).until(ec.visibility_of_element_located((By.XPATH, '/html/body/div[3]/form/div[2]/div[3]/div/div[1]/button'))).click()
		time.sleep(15)
		cur_ip = WebDriverWait(browser, 10).until(ec.visibility_of_element_located((By.XPATH, '//*[@id="page"]/div[2]/form/div/div[2]/table/tbody/tr[1]/td[4]'))).text
		browser.quit()
		markup = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = 2)
		yes = types.KeyboardButton('OK')
		no = types.KeyboardButton('Change')
		back = types.KeyboardButton('↩️Back')
		markup.add(yes, no, back)
		bot.send_message(message.chat.id, f'Done! Current IP is: <b>{cur_ip}</b>, okay?', parse_mode = 'html', reply_markup = markup)
		bot.register_next_step_handler(message, ip_change_st3)
	else:
		bot.send_message(message.chat.id, f'Repeat your request', parse_mode = 'html')
		bot.register_next_step_handler(message, ip_change_st2)




def ip_change_st1(message):
	bot.send_message(message.chat.id, 'Working...',parse_mode = 'html', reply_markup = types.ReplyKeyboardRemove())
	chrome_options = Options()
	chrome_options.add_argument('--headless')
	chrome_options.add_argument('--no-sandbox')
	chrome_options.add_argument('--disable-dev-shm-usage')
	browser = webdriver.Chrome(service = Service(ChromeDriverManager(chrome_type = ChromeType.CHROMIUM).install()), options = chrome_options)
	try:
		browser.get('http://admin:admin@192.168.1.1')
	except Exception:
		bot.send_message(message.chat.id, 'Error connecting to host', parse_mode = 'html')
		browser.quit()
		return
	markup = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = 2)
	yes = types.KeyboardButton('Yes')
	no = types.KeyboardButton('Cancel')
	back = types.KeyboardButton('↩️Back')
	markup.add(yes, no, back)
	cur_ip = WebDriverWait(browser, 10).until(ec.visibility_of_element_located((By.XPATH, '/html/body/div[2]/div[1]/div/div/div[2]/form/div/div/div[2]/div[1]/div/div[1]/div/table/tbody/tr[2]/td[2]'))).text
	browser.quit()
	bot.send_message(message.chat.id, f'Current IP: <b>{cur_ip}</b>, change it?', parse_mode = 'html', reply_markup = markup)
	bot.register_next_step_handler(message, ip_change_st2)




def auto_ip_change(message):
	chrome_options = Options()
	chrome_options.add_argument('--headless')
	chrome_options.add_argument('--no-sandbox')
	chrome_options.add_argument('--disable-dev-shm-usage')
	browser = webdriver.Chrome(service = Service(ChromeDriverManager(chrome_type = ChromeType.CHROMIUM).install()), options = chrome_options)
	try:
		browser.get('http://admin:admin@192.168.1.1')
	except Exception:
		browser.quit()
		return
	cur_ip = WebDriverWait(browser, 10).until(ec.visibility_of_element_located((By.XPATH, '/html/body/div[2]/div[1]/div/div/div[2]/form/div/div/div[2]/div[1]/div/div[1]/div/table/tbody/tr[2]/td[2]'))).text
	while cur_ip[:2] not in ['94', '95']:
		bot.send_message(message.chat.id, 'Grey IP detected, changing...',parse_mode = 'html')
		try:
			WebDriverWait(browser, 10).until(ec.visibility_of_element_located((By.XPATH, '//*[@id="page_frame"]/div[2]/div/ul/li[2]/a'))).click()
			WebDriverWait(browser, 10).until(ec.visibility_of_element_located((By.XPATH, '//*[@id="page"]/div[2]/form/div/div[2]/table/tbody/tr[1]'))).click()
			# WebDriverWait(browser, 10).until(ec.visibility_of_element_located((By.XPATH, '/html/body/div[3]/form/div[2]/div[3]/div/div[2]/button'))).click()
			WebDriverWait(browser, 10).until(ec.visibility_of_element_located((By.XPATH, '/html/body/div[3]/form/div[2]/div[3]/div/div[1]/button'))).click()
			time.sleep(15)
			cur_ip = WebDriverWait(browser, 10).until(ec.visibility_of_element_located((By.XPATH, '//*[@id="page"]/div[2]/form/div/div[2]/table/tbody/tr[1]/td[4]'))).text
		except Exception:
			bot.send_message(message.chat.id, 'Error IP changing',parse_mode = 'html')
			browser.quit()
			return
		if cur_ip[:2] in ['94', '95']:
			bot.send_message(message.chat.id, f'Changed! Current IP is {cur_ip}',parse_mode = 'html')
	browser.quit()


#Create buttons
def buttons(message):
	markup = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = 3)
	hashrate = types.KeyboardButton('Hashrate')
	total_hashrate = types.KeyboardButton('Total Hashrate')
	total_info = types.KeyboardButton('Info')
	status = types.KeyboardButton('Status')
	settings = types.KeyboardButton('Settings⚙️')
	wallet = types.KeyboardButton('My Wallet')
	income = types.KeyboardButton('Income')
	ip_change = types.KeyboardButton('IP change')
	difficulty = types.KeyboardButton('Difficulty')
	markup.add(hashrate, total_hashrate, total_info, difficulty, wallet, income, status, settings, ip_change)
	bot.send_message(message.chat.id,'What you wanna know?', reply_markup = markup)

def scheduler(message ,common_hr):
	schedule.every().hour.do(auto_ip_change, message)
	schedule.every().day.at('17:00').do(check_gminer, message)
	# schedule.every(15).minutes.do(smart_status, message, True)
	# schedule.every(10).minutes.do(average_income_calc, message, get_wallet(message, True))
	try:
		while True:
			schedule.run_pending()
			time.sleep(1)
	except Exception as e:
		print (f'scheduler down, restarting...{e}')
		

avg_income = 0
avg_income_list = [0] * 30
schedule_started = False
bot = telebot.TeleBot(bot_settings.Token)

#Message from user checking
@bot.message_handler()
def message_check(message):
	global schedule_started
	if message.text == '/help':
		buttons(message)
		if not schedule_started:
			t = Thread(target = scheduler, args = (message, bot_settings.common_hr))
			t.daemon = True
			t.start()
			schedule_started = True
	elif message.text == 'Hashrate':
		hashrate(message)
	elif message.text == 'Info':
		total_info(message)
	elif message.text == 'Total Hashrate':
		total_hashrate(message)
	elif message.text == 'Status':
		smart_status(message)
	elif message.text == 'My Wallet':
		get_wallet(message)
	elif message.text == 'Income':
		bot.send_message(message.chat.id,f'Yor current income: <b>{round(avg_income, 2)}</b> RUB/day',parse_mode='html')
	elif message.text == 'Difficulty':
		difficulty(message)
	elif message.text == 'Settings⚙️':
		settings_st1(message)
	elif message.text == 'IP change':
		ip_change_st1(message)
	elif message.text == '↩️Back':
		buttons(message)
	else:
		mess = f'Hi, <b>{message.from_user.first_name}</b>, use /help command for help'
		bot.send_message(message.chat.id,mess,parse_mode='html')


bot.infinity_polling()


