import time
import json
from copy import deepcopy
import os

# 数据模型

def autosave(func):
    def __autosave(self, *args, **kws):
        ret = func(self, *args, **kws)
        if self.autosave:
            with open(self.file, "wt", encoding='utf-8') as f:
                f.write(json.dumps(self.getall(), ensure_ascii=False))
        return ret
    return __autosave


class Model:
    def __init__(self, data=None, file='data.json', autosave=True):
        if data is not None:
            self.__data.update(data)
        else:
            self.__data = {}
        self.file = os.path.join(os.path.split(__file__)[0], file)
        self.autosave=autosave
        try:
            self.load()
        except FileNotFoundError:
            self.save()

    @autosave
    def update(self, uid, stuid=None, choices=None, address=None, lasttime=None):
        if self.__data.get(uid):
            update_data = {'stuid': stuid,
                           'choices': choices,
                           'address': address,
                           'lasttime': lasttime}
            for key in list(update_data.keys()):
                if update_data[key] is None:
                    update_data.pop(key)
            self.__data[uid].update(deepcopy(update_data))
        else:
            if stuid is None:
                raise ValueError('stuid can not be None!')
            self.__data.update({
                uid: {'stuid': stuid,
                      'choices': '211' if choices is None else choices,
                      'address': u"成都市" if address is None else address,
                      'lasttime': time.strftime('%m%d', time.localtime(time.time()-24*3600))}})
    
    def get(self, uid):
        return deepcopy(self.__data.get(uid))

    @autosave
    def delete(self, uid):
        return self.__data.pop(uid)

    def getall(self):
        return deepcopy(self.__data)

    def load(self):
        with open(self.file, 'rt', encoding='utf-8') as f:
            self.__data.update(json.loads(f.read()))

    def save(self):
        with open(self.file, "wt", encoding='utf-8') as f:
            f.write(json.dumps(self.__data, ensure_ascii=False))


database = Model()

if __name__ == '__main__':
    model = Model()
    tid = '490328928'
    print(model._Model__data)
    model.update(tid, '201922021807')
    print('1:' + str(model._Model__data))
    model.update(tid, choices='2121')
    print('2:' + str(model._Model__data))
    #model.save()
    #model.delete(tid)
    #print('3:' + str(model._Model__data))
    #model.load()
    #print('4:' + str(model._Model__data))
