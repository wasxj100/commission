import pandas as pd

import configparser
data = {'name': ['毛毛', '小妮'], 'pp': [3, 4], 'p1': [0, 1],'p2': [0, 4], 'p3': [4, 2], 'p4': [0, 2], 'p5': [2, 0], 'm1': [1, 3],
        'm2': [1, 1], 'm3': [2, 3], 'd1': [0, 0], 'd2': [1, 3], 'd3': [1, 1], 'p12':[1,0]}
VALUE = [20, 5, 2, 2, 3, 5, 30, 10, 40, 30, 10, 40, 20]
data1 = pd.DataFrame(data)
print(data1)
data2 = data1.iloc[:,1:] * VALUE

data2['求和'] = data2.sum(axis = 1)
print(data2)

conf = configparser.ConfigParser()

conf.read('config.ini', encoding='utf-8')
a = conf.items('fields')
print(a)
b = [int(i) for i in dict(conf['amounts']).values()]
print(b)