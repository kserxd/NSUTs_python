import base64
import shutil
import zipfile
import vscode
from nsuts_base import NsutsClient
import os, json
from tools import MDCreator, DB
from vscode.context import Context
import sys

ext = vscode.Extension("NSUTs")

user = NsutsClient()

config = {}

database = DB("login.json")


@ext.event
async def on_activate():
    vscode.log("Started!")

@ext.command()
async def start(ctx: vscode.Context):
    return await progress(
        ctx,
        ext.commands[2].func,
        "Initialization of NSUTs workspace. It's might take a while",
    )

@ext.command()
async def reload(ctx: vscode.Context):
    if not config:
        await login(ctx)
    return await ctx.show(vscode.InfoMessage("Reload"))

@ext.command()
async def login(ctx: vscode.Context, update=False):
    await user_info(ctx)
    try:
        user.auth()
    except:
        await ctx.show(
            vscode.ErrorMessage("Incorrect login, password or url! Try again!")
        )
        database.remove("url")
        database.remove("login")
        database.remove("password")
        database.save()
        await login(ctx, update)
    if update:
        init_workspace()
    await ctx.show(vscode.InfoMessage(f'Logged into {user.config["email"]}'))
    return await ctx.env.ws.run_code(
        'vscode.commands.executeCommand("vscode.openFolder", '
        + "vscode.Uri.file('/home/deu/.nsuts')"
        + ")"
    )

# python
# c
# c++
# java
# text
@ext.command(keybind="shift+f5")
async def build_and_run(ctx: vscode.Context):  # TODO add handler for other languages
    path = (
        "/".join(
            (
                await ctx.env.ws.run_code(
                    "vscode.window.activeTextEditor.document.uri.fsPath", thenable=False
                )
            ).split("/")[:-1]
        )
        + "/"
    )
    clear_executable(os.path.join(path, "main"))
    result = compile_c_files(path)
    res = await ctx.window.active_terminal
    await res.send_text(f"clear && {result}")
    return res

@ext.command(keybind="shift+f4")
async def submit(ctx: vscode.Context):
    if not config:
        await login(ctx)
    path, file_path = await get_open_file_path(ctx)
    for i in os.listdir(path):
        try:
            if i.index("_temp"):
                os.remove(path + i)
        except:
            pass
    compil = await choose_compilator(ctx, path)
    error = False
    try:
        if compil.index("email"):
            zip_path = shutil.make_archive(
                "/".join(path.split("/")[:-2]) + "/main", "zip", path
            )
            try:
                user.submit_solution(
                    await choose_olymp_tour_task_by_path(path),
                    compil.split()[-1],
                    zip_path,
                )
            except:
                await ctx.show(
                    vscode.ErrorMessage(
                        "Your submit return error. It might be caused by:\n - Empty file\n - Incorrect compilator\n - Last submit on this task is same"
                    )
                )
                error = True
            os.remove(zip_path)
    except ValueError:
        try:
            user.submit_solution(
                await choose_olymp_tour_task_by_path(path),
                compil.split()[-1],
                open(file_path, "r").read(),
            )
        except:
            error = True
            await ctx.show(
                vscode.ErrorMessage(
                    "Your submit return error. It might be caused by Empty file, Incorrect compilator or Last submit on this task is same"
                )
            )
    if not error:
        await ctx.show(vscode.InfoMessage(f"Task '{file_path.split('/')[-1]}' sent!"))
        await progress(ctx, get_result, "Waiting for result")


async def choose_compilator(ctx: Context, path):
    items = []
    await choose_olymp_tour_task_by_path(path)
    for i in user.get_compilators():
        items.append(vscode.QuickPickItem(label=i["title"], detail=f"Id: {i['id']}"))
    result = await ctx.window.show(
        vscode.QuickPick(
            items, vscode.QuickPickOptions("Choose comilator", match_on_detail=True)
        )
    )
    return result.detail

async def progress(ctx: vscode.Context, command, text):
    # Show a progress bar in the status bar
    async with ctx.window.progress(text, vscode.ProgressLocation.Notification) as p:
        res = await command(ctx, True)
    await ctx.window.show(vscode.InfoMessage("Completed!"))

async def get_result(ctx: vscode.Context, temp=True):
    path, file_path = await get_open_file_path(ctx)
    result = user.get_result()
    while result == None:
        result = user.get_result()
    text = ""
    if result[-1] == "A":
        text = "Accepted!"
    else:
        text = f"Error on test {len(result)}"
        with open(path + "result_temp.txt", "w") as f:
            data = user.get_solution_source(user.get_my_last_submit_id())
            if type(data) == dict:
                f.write(data["result"].decode())
    # get_solution_source
    await ctx.show(vscode.InfoMessage(text))

async def get_open_file_path(ctx: vscode.Context):
    file_path = await ctx.env.ws.run_code(
        "vscode.window.activeTextEditor.document.uri.fsPath", thenable=False
    )
    return ["/".join(file_path.split("/")[:-1]) + "/", file_path]

async def user_info(ctx: vscode.Context, change=False):
    if change:
        input_box = vscode.InputBox("Email", place_holder="example@test.test")
        res = await ctx.show(input_box)
        database.write("login", res)
        input_box = vscode.InputBox("Password", password=True)
        res = await ctx.show(input_box)
        database.write("password", res)
        input_box = vscode.InputBox(
            "URL", place_holder="https://fresh.nsuts.ru/nsuts-new"
        )
        res = await ctx.show(input_box)
        if res[-1] == "/":
            res[:-1]
        database.write("url", res)
    else:
        if database.read("login") == "ERROR":
            input_box = vscode.InputBox("Email", place_holder="example@test.test")
            res = await ctx.show(input_box)
            database.write("login", res)

        if database.read("password") == "ERROR":
            input_box = vscode.InputBox("Password", password=True)
            res = await ctx.show(input_box)
            database.write("password", res)

        if database.read("url") == "ERROR":
            input_box = vscode.InputBox(
                "URL", place_holder="https://fresh.nsuts.ru/nsuts-new"
            )
            res = await ctx.show(input_box)
            if res[-1] == "/":
                res[:-1]
            database.write("url", res)

    database.save()

    user.config["nsuts"] = database.read("url")
    user.config["email"] = database.read("login")
    user.config["password"] = database.read("password")


def load_task(task, path):
    if not os.path.isdir(path):
        os.mkdir(path)
    download_accepted(task, path)
    return path

def download_accepted(task, path):
    data = user.get_task_id_by_name(
        task["title"].replace(" ", "_").replace("(", "").replace(")", "")
    )
    data = user.download_task(data)
    if data:
        if data[-1] == "emailtester":
            result = decode(data[1])
            with open(path + "/files.zip", "wb") as f:
                f.write(decode(data[0]))
            try:
                with zipfile.ZipFile(path + "/files.zip", "r") as zip_ref:
                    zip_ref.extractall(path)
                os.remove(path + "/files.zip")
            except zipfile.BadZipFile:
                os.rename(path + "/files.zip", path + "/main.c")
            return result
        else:
            result = ""
            for i in data[0]:
                result += decode(i).decode()
            with open(path + "/main.c", "w") as f:
                f.write(result)


def init_workspace():
    home_path = os.path.expanduser("~") + "/.nsuts"
    if not os.path.isdir(home_path):
        os.mkdir(home_path)
    for olymp in user.get_olympiads():
        olymp_path = load_olymp(
            olymp,
            home_path
            + f"/{olymp['title'].replace(' ', '_').replace('(', '').replace(')', '')}",
        )
        for tour in user.get_tours():
            tour_path = load_tour(
                tour,
                olymp_path
                + f"/{tour['title'].replace(' ', '_').replace('(', '').replace(')', '')}",
            )
            for task in user.get_tasks():
                task_path = load_task(
                    task,
                    tour_path
                    + f"/{task['title'].replace(' ', '_').replace('(', '').replace(')', '')}",
                )

def load_olymp(olymp, path):
    if not os.path.isdir(path):
        os.mkdir(path)
    user.select_olympiad(olymp["id"])
    return path

def load_tour(tour, path):
    if not os.path.isdir(path):
        os.mkdir(path)
    user.select_tour(tour["id"])
    if not os.path.exists(path + "/statement.pdf"):
        user.download_tour_statement(path)
    result = json.loads(load_reports(path))
    temp = MDCreator(result)
    temp.sort()
    temp.create_md(path + "/results.md")

    return path


def choose_olymp_tour_task_by_path(path):
    home_path = os.path.expanduser("~") + "/.nsuts"
    path = path.replace(home_path, "")[1:].split("/")
    user.select_olympiad(user.get_olympiad_id_by_name(path[0]))
    user.select_tour(user.get_tour_id_by_name(path[1]))
    return user.get_task_id_by_name(path[2])

def clear_executable(path):
    if os.path.exists(path):
        os.remove(path)

def compile_c_files(directory):
    # Get the list of C files in the directory
    c_files = [f for f in os.listdir(directory) if f.endswith(".c")]
    os_name = sys.platform.lower()
    if os_name == "windows":
        compiler = "gcc"
    elif os_name == "linux" or os_name == "darwin":
        compiler = "clang"
    else:
        raise Exception(f"Unsupported operating system: {os_name}")
    command = f'{compiler} -w -lm -o "{directory}main" '
    # Compile each C file
    for c_file in c_files:
        filename = os.path.join(directory, c_file)
        command += f'"{filename}" '
    os.system(command)
    return os.path.join(directory, "main")

def decode(data):
    return base64.b64decode(data)

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
        if reports[-1] != i:
            json_text += ","
    json_text += "]}"

    return json_text

ext.run()
