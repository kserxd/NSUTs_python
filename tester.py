import os
import shutil
from nsuts_base import NsutsClient


user = NsutsClient()

user.config['nsuts'] = 'https://fresh.nsuts.ru/nsuts-new'
user.config['email'] = 'a.dunaev@g.nsu.ru'
user.config['password'] = '6_KeSaR_6'

user.auth()

# for olymp in user.get_olympiads():
#     user.select_olympiad(olymp['id'])
#     print(olymp['title'])
#     for tour in user.get_tours():
#         user.select_tour(tour['id'])
#         print("->", tour['title'])
#         for task in user.get_tasks():
#             data = {i['task_id']: i['id'] for i in user.get_reports() if i['result_line'][-1] == "A"}
#             result = ''
#             try:
#                 result = data[task['id']]
#             except:
#                 pass
#             finally:
#                 print(result)

            
#         print()
path = '/home/deu/.nsuts/Программирование_23XXX/Набор_задач_X2_2024.02.15/[ET]_2._Арифметика_по_модулю'
a = shutil.make_archive('/'.join(path.split('/')[:-1]) + '/main', 'zip', path)
print(open(a, 'rb').read())
print(open('result.txt', 'r').read())