import base64
from pathlib import Path
import shutil
import zipfile
import vscode
import nsuts_base
import os, json
from md_creator import MDCreator
from vscode.context import Context

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
    os.system(command)
    return os.path.join(directory, 'main')

@ext.event
async def on_activate():
    vscode.log('Started!')

def decode(data):
    return base64.b64decode(data)

@ext.command()
async def reload(ctx: vscode.Context):
    return await ctx.show(vscode.InfoMessage("Reload"))


def load_olymp(olymp, path):
    if (not os.path.isdir(path)): os.mkdir(path)
    user.select_olympiad(olymp['id'])
    return path

def load_tour(tour, path):
    if (not os.path.isdir(path)): 
        os.mkdir(path) 
    user.select_tour(tour['id'])
    if (not os.path.exists(path + '/statement.pdf')): user.download_tour_statement(path)
    result = json.loads(load_reports(path))
    temp = MDCreator(result)
    temp.sort()
    temp.create_md(path + "/results.md")

    return path

def load_reports(path):
    json_text = '{"submits":['
    reports = user.get_reports()
    for i in reports:
        json_text += "{"
        json_text += f'"id" : {i["id"]},'
        json_text += f'"task_id" : {i["task_id"]},'
        json_text += f'"task_title" : "{i["task_title"]}",'
        json_text += f'"compiler" : "{i["compiler"]}",'
        json_text += f'"result_line" : "{i["result_line"]}",'
        json_text += f'"date" : "{i["date"]}",'
        json_text += f'"points" : {user.get_points(int(i["id"]))}'
        json_text += "}"
        if (reports[-1] != i): json_text += ','
    json_text += ']}'

    return json_text

async def load_task(task, path):
    if (not os.path.isdir(path)): 
        os.mkdir(path)
    await download_accepted(task, path)
    return path
            
async def download_accepted(task, path): #TODO 
    data = user.get_task_id_by_name(task['title'].replace(' ', '_').replace('(', '').replace(')', ''))
    data = user.download_task(data)
    if (data):
        if (data[-1] == 'emailtester'):
            result = decode(data[1])
            with open(path + '/files.zip', 'wb') as f: f.write(decode(data[0]))
            try:
                with zipfile.ZipFile(path + '/files.zip', 'r') as zip_ref:
                    zip_ref.extractall(path)
                os.remove(path + '/files.zip')
            except zipfile.BadZipFile:
                os.rename(path + '/files.zip', path + '/main.c')
        else:
            result = ''
            for i in data[0]:
                result += decode(i).decode()
            with open(path + "/main.c", 'w') as f: f.write(result)


async def init_workspace(user:nsuts_base.NsutsClient):
    home_path = os.path.expanduser("~") + "/.nsuts"
    if (not os.path.isdir(home_path)): os.mkdir(home_path) 
    for olymp in user.get_olympiads():
        olymp_path = load_olymp(olymp, home_path + f"/{olymp['title'].replace(' ', '_').replace('(', '').replace(')', '')}")
        for tour in user.get_tours():
            tour_path = load_tour(tour, olymp_path + f"/{tour['title'].replace(' ', '_').replace('(', '').replace(')', '')}")
            for task in user.get_tasks():
                task_path = await load_task(task, tour_path + f"/{task['title'].replace(' ', '_').replace('(', '').replace(')', '')}")
                            

@ext.command()
async def login(ctx: vscode.Context, update=False):
    if (database.read('login') == "ERROR"):
        input_box = vscode.InputBox("Email")
        res = await ctx.show(input_box)
        database.write('login', res)
    
    if (database.read('password') == "ERROR"):
        input_box = vscode.InputBox("Password", password=True)
        res = await ctx.show(input_box)
        database.write('password', res)

    if (database.read('url') == "ERROR"):
        input_box = vscode.InputBox("URL")
        res = await ctx.show(input_box)
        database.write('url', res)
    
    database.save()

    user.config['nsuts'] = database.read('url')
    user.config['email'] = database.read('login')
    user.config['password'] = database.read('password')
    
    user.auth()
    if (update):
        await init_workspace(user)
    await ctx.show(vscode.InfoMessage(f'Logged into {user.config["email"]}'))
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
    file_path = await ctx.env.ws.run_code('vscode.window.activeTextEditor.document.uri.fsPath', thenable = False)
    path = '/'.join(file_path.split('/')[:-1]) + '/'
    compil = await choose_compilator(ctx, path)
    try:
        if (compil.index("email")):
            zip_path = shutil.make_archive('/'.join(path.split('/')[:-2]) + '/main', 'zip', path)
            user.submit_solution(await choose_olymp_tour_task_by_path(path), compil.split()[-1], zip_path)
            os.remove(zip_path)
    except ValueError:
        user.submit_solution(await choose_olymp_tour_task_by_path(path), compil.split()[-1], open(file_path, 'r').read())
    await ctx.show(vscode.InfoMessage(f"Task '{file_path.split('/')[-1]}' sent!"))

async def choose_olymp_tour_task_by_path(path):
    home_path = os.path.expanduser('~') + "/.nsuts"
    path = path.replace(home_path, '')[1:].split('/')
    
    user.select_olympiad(user.get_olympiad_id_by_name(path[0]))
    user.select_tour(user.get_tour_id_by_name(path[1]))
    return user.get_task_id_by_name(path[2])

async def choose_compilator(ctx: Context, path):
    items = []
    await choose_olymp_tour_task_by_path(path)
    for i in user.get_compilators():
        items.append(vscode.QuickPickItem(label=i['title'], detail=f"Id: {i['id']}"))
    result = await ctx.window.show(vscode.QuickPick(items, vscode.QuickPickOptions('Choose comilator', match_on_detail=True)))
    return result.detail

async def progress(ctx: vscode.Context, command):
    # Show a progress bar in the status bar
    async with ctx.window.progress("Initialization of NSUTs workspace. It's might take a while", vscode.ProgressLocation.Notification) as p:
        res = await command(ctx, True)
    await ctx.window.show(vscode.InfoMessage("Completed!"))



@ext.command()
async def start(ctx: vscode.Context):
    return await progress(ctx, ext.commands[1].func)

ext.run()