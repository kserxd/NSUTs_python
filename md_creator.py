
class MDCreator:
    def __init__(self, data : dict):
        self.data = data

    def sort(self):
        try:
            self.data['submits'] = sorted(self.data['submits'], key=lambda x: int(x['task_title'].split('.')[0].replace("[ET]", "")))
        except KeyError:
            pass
    def unique(self):
        lst = -1
        result = []
        for i in self.data['submits']:
            if (i['task_id'] != lst): 
                lst = i['task_id']
                result.append(i)
        return result

    def create_md(self, path):
        with open(path, 'w') as f:
            data = '''
| Number |  Id | Task id | Name | Compiler | Result | Points | Code | 
| ----------- | ----------- | ----------- | ----------- | ----------- | ----------- | ----------- | ----------- |
'''
            for i in self.unique():
                data += f'| {int(i["task_title"].split(".")[0].replace("[ET]", ""))} | {i["id"]} | {i["task_id"]} | {i["task_title"]} | {i["compiler"]} | {"Accepted!" if i["result_line"][-1] == "A" else "Error"} | {i["points"]} | {"```None```"} |\n'
            f.write(data)