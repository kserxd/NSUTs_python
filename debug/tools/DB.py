import os, json

class DB:
    def __init__(self, filename):
        self.filename = filename
        if (not os.path.exists(filename)):
            f = open(filename, "w")
            f.write("{}")
            f.close()
        self.rfp = open(filename, "r")
        self.data = json.load(self.rfp)
        
    def write(self, key, data):
        self.data[key] = data
        self.save()

    def read(self, key = None):
        if (key):
            try:
                return self.data[key]
            except:
                return "ERROR"
        else:
            return self.data
    
    def remove(self, key):
        self.data.pop(key)

    def save(self):
        json.dump(self.data, open(self.filename, "w"))

    def close(self):
        self.fp.close()
