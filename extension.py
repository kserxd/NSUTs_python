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

    # Compile each C file
    for c_file in c_files:
        filename = os.path.join(directory, c_file)
        print(f"Compiling {filename}")

        # Determine the operating system
        os_name = sys.platform.system().lower()

        # Use the appropriate compiler for the OS
        if os_name == 'windows':
            compiler = 'gcc'
        elif os_name == 'linux' or os_name == 'darwin':
            compiler = 'clang'
        else:
            raise Exception(f"Unsupported operating system: {os_name}")

        # Compile the C file using the appropriate compiler
        command = f"{compiler} -o {c_file} {filename}"
        print(command)
        os.system(command)

@ext.event
async def on_activate():
    vscode.log(f"The ext '{ext.name}' started!")

@ext.command()
async def reload(ctx: vscode.Context):
    return await ctx.show(vscode.InfoMessage("Reload"))

def init_workspace(user:nsuts_base.NsutsClient):
    home_path = os.path.expanduser('~') + "/.nsuts"
    if (not os.path.isdir(home_path)): os.mkdir(home_path) 
    for olymp in user.get_olympiads():
        olymp_path = home_path + f"/{olymp['title']}"
        if (not os.path.isdir(olymp_path)): os.mkdir(olymp_path) 
        user.select_olympiad(olymp['id'])
        for tour in user.get_tours():
            tour_path = olymp_path + f"/{tour['title']}"
            if (not os.path.isdir(tour_path)): os.mkdir(tour_path) 
            user.select_tour(tour['id'])
            if (not os.path.exists(tour_path + '/statement.pdf')): user.download_tour_statement(tour_path)
            for task in user.get_tasks():
                task_path = tour_path + f"/{task['title']}"
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
    return await ctx.show(vscode.InfoMessage(f'test'))

@ext.command(keybind="shift+f5")
async def build_and_run(ctx: vscode.Context):
    return vscode.log(ctx.window.active_text_editor)

@ext.command()
async def panel(ctx: vscode.Context):
    return await ctx.env.ws.run_code('vscode.commands.executeCommand("vscode.openFolder", ' + 
                              "vscode.Uri.file('/home/deu/.nsuts')" + 
                              ')')

@ext.command()
async def main(ctx):
    pass


ext.run()