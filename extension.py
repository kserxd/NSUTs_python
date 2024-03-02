import vscode
import nsuts_base
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

    def save(self):
        json.dump(self.data, open(self.filename, "w"))

    def close(self):
        self.fp.close()

ext = vscode.Extension("NSUTs");

user = nsuts_base.NsutsClient();

config = {}

database = DB('login.json')


import sys

def compile_c_files(directory):
    # Get the list of C files in the directory
    c_files = [f for f in os.listdir(directory) if f.endswith('.c')]
    os_name = sys.platform.lower()
    if os_name == 'windows':
        compiler = 'gcc'
    elif os_name == 'linux' or os_name == 'darwin':
        compiler = 'clang'
    else:
        raise Exception(f"Unsupported operating system: {os_name}")
    command = f'{compiler} -w -lm -o "{directory}main" '
    # Compile each C file
    for c_file in c_files:
        filename = os.path.join(directory, c_file)
        command += f'"{filename}" '
    vscode.log(command)
    os.system(command)
    return os.path.join(directory, 'main')

from vscode.context import Context
@ext.event
async def on_activate():
    await ext.commands[1].func(Context(ext.ws))

@ext.command()
async def reload(ctx: vscode.Context):
    return await ctx.show(vscode.InfoMessage("Reload"))

def init_workspace(user:nsuts_base.NsutsClient):
    home_path = os.path.expanduser('~') + "/.nsuts"
    if (not os.path.isdir(home_path)): os.mkdir(home_path) 
    for olymp in user.get_olympiads():
        olymp_path = home_path + f"/{olymp['title'].replace(' ', '_').replace('(', '').replace(')', '')}"
        if (not os.path.isdir(olymp_path)): os.mkdir(olymp_path) 
        user.select_olympiad(olymp['id'])
        for tour in user.get_tours():
            tour_path = olymp_path + f"/{tour['title'].replace(' ', '_').replace('(', '').replace(')', '')}"
            if (not os.path.isdir(tour_path)): os.mkdir(tour_path) 
            user.select_tour(tour['id'])
            if (not os.path.exists(tour_path + '/statement.pdf')): user.download_tour_statement(tour_path)
            with open(tour_path + '/reports.json', 'w') as f:
                f.write('{"submits":[')
                reports = user.get_reports()
                for i in reports:
                    f.write("{")
                    f.write(f'"id" : {i["id"]},')
                    f.write(f'"task_id" : {i["task_id"]},')
                    f.write(f'"task_title" : "{i["task_title"]}",')
                    f.write(f'"compiler" : "{i["compiler"]}",')
                    f.write(f'"result_line" : "{i["result_line"]}",')
                    f.write(f'"date" : "{i["date"]}"')
                    f.write("}")
                    if (reports[-1] != i): f.write(',') 
                f.write(']}')
                vscode.log(tour)
            for task in user.get_tasks():
                task_path = tour_path + f"/{task['title'].replace(' ', '_').replace('(', '').replace(')', '')}"
                if (not os.path.isdir(task_path)): os.mkdir(task_path)


            

@ext.command()
async def login(ctx: vscode.Context):
    if (database.read('login') == "ERROR"):
        input_box = vscode.InputBox("Email")
        res = await ctx.show(input_box)
        print(res)
        database.write('login', res)
    
    if (database.read('password') == "ERROR"):
        input_box = vscode.InputBox("Password", password=True)
        res = await ctx.show(input_box)
        print(res)
        database.write('password', res)

    if (database.read('url') == "ERROR"):
        input_box = vscode.InputBox("URL")
        res = await ctx.show(input_box)
        print(res)
        database.write('url', res)
    
    database.save()

    user.config['nsuts'] = database.read('url')
    user.config['email'] = database.read('login')
    user.config['password'] = database.read('password')
    
    user.auth()
    init_workspace(user)
    await ctx.show(vscode.InfoMessage(f'test'))
    return await ctx.env.ws.run_code('vscode.commands.executeCommand("vscode.openFolder", ' + 
                              "vscode.Uri.file('/home/deu/.nsuts')" + 
                              ')')

def clear_executable(path):
    if (os.path.exists(path)): os.remove(path)

@ext.command(keybind="shift+f5")
async def build_and_run(ctx: vscode.Context):
    path = '/'.join((await ctx.env.ws.run_code('vscode.window.activeTextEditor.document.uri.fsPath', thenable = False)).split('/')[:-1]) + '/'
    clear_executable(os.path.join(path, 'main'))
    result = compile_c_files(path)
    res = await ctx.window.active_terminal
    await res.send_text(f'clear && {result}')
    return res

@ext.command(keybind="shift+f4")
async def submit(ctx: vscode.Context):
    pass

@ext.command()
async def main(ctx: vscode.Context):
    return 0

ext.run()