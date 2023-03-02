import requests
import time
from selenium import webdriver
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

def parse_2miners():
	wallet = 'bc1qzcezx5ngl7ngd4a4h2hcrkqxgg3tgp294ck4wu'
	browser = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
	browser.get(f'https://eth.2miners.com/ru/account/{wallet}')
	topay_elem = browser.find_element(By.XPATH, '//*[@id="miner-info"]/div/div[1]/div/div/div[2]/div/div[1]/h4/span[1]')
	pay_for_day_elem = browser.find_element(By.XPATH, '//*[@id="miner-info"]/div/div[3]/div/div/div[2]/div[1]/div[2]/span[1]')
	print (pay_for_day_elem.text)
	print (topay_elem.text)


def average_income_calc():
	wallet = 'bc1qzcezx5ngl7ngd4a4h2hcrkqxgg3tgp294ck4wu'
	browser = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
	browser.get(f'https://eth.2miners.com/ru/account/{wallet}')
	pay_for_day_elem = browser.find_element(By.XPATH, '//*[@id="miner-info"]/div/div[3]/div/div/div[2]/div[1]/div[2]/span[1]')
	pay_for_day = pay_for_day_elem.text
	indx = pay_for_day.find(' ')
	pay_for_day = float(pay_for_day[indx+1:])
	print(pay_for_day)
	return pay_for_day
#parse_2miners()
average_income_calc()
























def check_gminer(message, rig):
	git = "https://github.com/develsoftware/GMinerRelease/releases"
	browser = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
	curr_release = 0
	for i in rig:
		browser.get(f'http://{i}')
		curr_release_elem = browser.find_element(By.ID, 'miner_name')
		curr_release_rig = curr_release_elem.text
		for j in curr_release_rig:
			if not j.isdecimal():
				curr_release_rig = curr_release_rig.replace(j, '')
		if int(curr_release_rig) > curr_release:
			curr_release = int(curr_release_rig)
		print (curr_release)

	browser.get(git)
	release_elem = browser.find_element(By.TAG_NAME, 'h1')
	release = release_elem.text
	for i in release:
		if not i.isdecimal():
			release = release.replace(i, '')
	if int(release) > curr_release:
		bot.send_message(message.chat.id,f'New Gminer Release: {release}',parse_mode='html')
	print (release)
	browser.quit()
		#rigstat = requests.get(f'http://{i}', timeout = 1)
		#print (rigstat.text)
		#indx = rigstat.text.find('<td class="column_title" colspan="2" id="miner_name">GMiner 2.91</td>')
		#curr_release = rigstat.text[indx:indx+69]
		#print (indx)
		# for j in curr_release:
		# 	if not j.isdecimal:
		# 		curr_release = curr_release.replace(j, '')
		# print (curr_release)
	# try:
	# 	r = requests.get(git, timeout = 4)
	# except requests.exceptions.ConnectTimeout:
	# 	print('Shit')
	# #return False
	# res = r.text
	# indx = res.find('<a href="/develsoftware/GMinerRelease/releases/tag/')
	# release = res[indx:indx + 56]
	# for i in release:
	# 	if not i.isdecimal():
	# 		release = release.replace(i ,'')
	# print (release)
	
#check_gminer(rig)
