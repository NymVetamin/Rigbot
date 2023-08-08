from os import getenv
base_dir = '/etc/BOT/newbot_v10'
common_hr = 240 # Средний текущий хэшрейт
crit_temp = 75 # Критическая температура карт
crit_mem_temp = 100 #Критическая температура памяти карт
crit_power = 190 # Критическое потребление одной карты
Token = getenv('TOKEN')
Rig_addr = ['192.168.88.3:20030', '192.168.88.4:20030'] # Список ригов