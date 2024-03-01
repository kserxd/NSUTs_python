from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import Select

import requests
import os
import shutil

from typing import *

os.umask(0)

from time import sleep
import json

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

class Row:
    def __init__(self, elements):
        string = elements[2].text.replace("[ET] ", '').split()
        self.number = int(string[0].replace('.', ''))
        self.code : WebElement = elements[1]
        self.name = ' '.join(string[1:])
        self.compiler = elements[3].text
        self.state = elements[4].text
        self.test = elements[5].text
        self.raw_name = elements[2].text
    
    def __str__(self):
        return f"{self.number}. {self.name}\t\t{self.compiler}\t{self.state}\t{self.test}" 

    def __repr__(self):
        return f"{self.number}. {self.name}\t\t{self.compiler}\t{self.state}\t{self.test}" 

    def __eq__(self, other):
        return self.number == other.number

class Table:
    def __init__(self, driver, xpath):
        self.rows = len(driver.find_elements(By.XPATH, xpath + "/tr"))
        self.col = len(driver.find_elements(By.XPATH, xpath + "/tr[1]/td"))
        self.elements : List[Row] = []
        for i in range(self.rows):
            temp = []
            for j in range(self.col):
                temp.append(driver.find_element(By.XPATH, xpath + f"/tr[{i+1}]/td[{j+1}]"))
            self.elements.append(Row(temp))
        self.sort()
        self.del_if_accepted()

    def print(self):
        for i in range(self.rows):
            print(self.elements[i])

    def sort(self):
        self.elements.sort(key=lambda x: x.number)

    def del_if_accepted(self):
        temp = []
        lst = self.elements[0].number
        is_done = False
        for i in self.elements:
            if (lst != i.number):
                is_done = False
            if (not is_done):
                if i.state.find("ACCEPTED!") != -1:
                    for j in temp:
                        if (i.number == j.number):
                            break
                    else:
                        temp.append(i)
                        is_done = True
        
        self.elements = temp
        self.rows = len(temp)
    
    def unique(self):
        res : List[Row] = []
        for i in self.elements:
            if res:
                for j in res:
                    if (i.number == j.number):
                        break
                else:
                    res.append(i)
            else:
                res.append(i)
        return res

class NavBar:
    def __init__(self, driver, elem):
        self.driver = driver
        self.elem = elem
        self.name = elem.text

    def open(self):
        self.elem.click()

class Pack:
    def __init__(self, driver, elem, name):
        self.name = name;
        self.path = fr"{os.getcwd()}/{self.name}"
        
        self.driver : webdriver.Chrome  = driver
        self.elem = elem
        self.db = DB('login.json')
        self.elements : list
        self.navbars : list = []
        self.t : Table
        self.leaderboard : Table

    def load(self):
        self.elem.click()
        sleep(2)
        self.elements = self.driver.find_elements(By.TAG_NAME, "a")[5:-1]
        for i in self.elements[:-1]:
            self.navbars.append(NavBar(self.driver, i))
        
    
    def load_file(self):
        self.navbars[0].open()
        cookies = self.driver.get_cookies()[0]
        cookie_obj = requests.cookies.create_cookie(domain=cookies['domain'],name=cookies['name'],value=cookies['value'])
        s = requests.session()
        s.cookies.set_cookie(cookie_obj)
        r = s.get(self.elements[-1].get_attribute('href'))
        if not os.path.exists(self.path):
            os.makedirs(self.path)
        with open(self.path+"/tasks.pdf", "wb") as f:
            f.write(r.content)
        s.close()
        tasks = self.send_task(load_tasks=True)
        for i in tasks:
            path = f"{self.path}/{i.text.replace(' ', '_')}"
            if not os.path.exists(path):
                os.makedirs(path)
                f = open(path + "/main.c", "w")
                f.write('''
#include <stdio.h>
                    
int main(){
    return 0;
}
''')
            f.close()
        
        self.check_task()
        self.load_code()

    def send_task(self, number = None, load_tasks = False):
        self.navbars[1].open()
        sleep(1)
        selectable = self.driver.find_elements(By.TAG_NAME, 'select')
        compilers = selectable[0].find_elements(By.TAG_NAME, "option")[1:]
        tasks = selectable[1].find_elements(By.TAG_NAME, "option")[1:]
        comp = Select(selectable[0])
        task = Select(selectable[1])
        if (load_tasks):
            return tasks
        for i in os.listdir(self.path):
            if i.startswith(str(number)):
                temp = ''
                with open(self.path + "/" + i + '/main.c', "r") as fr:
                    temp = fr.read()
                comp.select_by_value('mingw8.1c')
                task.select_by_index(number)
                self.driver.find_element(By.ID, "source").send_keys(temp)
                self.driver.find_element(By.TAG_NAME, 'button').click()
                self.driver.find_elements(By.TAG_NAME, 'button')[1].click()
                sleep(1)
                break
            elif i.startswith(f"[ET]_{number}"):
                shutil.make_archive('main', 'zip', self.path + "/" + i)
                comp.select_by_value('emailtester')
                task.select_by_index(number)
                inp = self.driver.find_element(By.TAG_NAME, "input")
                inp.send_keys('/'.join(self.path.split('/')[:-1]) + "/main.zip")
                os.remove("main.zip")
                sleep(1)
                break
        else:
            print("not found :<")
        sleep(1)

    def check_task(self):
        self.navbars[2].open()
        sleep(1)
        self.t = Table(self.driver, '//table/tbody')
        self.t.print()

    def load_code(self):
        for i in self.t.unique():
            if (i.state.find("ACCEPTED!") != -1):
                i.code.click()
                tab1 = self.driver.window_handles[0]
                tab2 = self.driver.window_handles[1]
                sleep(1)
                self.driver.switch_to.window(tab2)
                
                if i.compiler.find("E-mail Tester") != -1:
                    el = self.driver.find_elements(By.TAG_NAME, 'button')[1:]
                    if (el):
                        code = self.driver.find_elements(By.TAG_NAME, 'code')
                        idx = 2
                        for j in el:
                            j.click()
                            sleep(1)
                            name = j.get_attribute('aria-controls')
                            self.update_code(i, code[idx+1].text, name)
                            idx+=2
                else:    
                    el = self.driver.find_elements(By.TAG_NAME, 'code')[1]
                    
                    self.update_code(i, el.text, "main.c")

                self.driver.close()
                self.driver.switch_to.window(tab1)
    
    def update_code(self, task : Row, code, name):
        path = f"{self.path}/{task.raw_name.replace(' ', '_')}"
        if not os.path.exists(path):
            os.makedirs(path)
        f = open(path + "/" + name, "w")
        f.write(code) 
        f.close()

    def get_leaderboard(self):
        self.navbars[3].open()
        sleep(1)
        # self.leaderboard = Table(self.driver, "//table/tbody")
        # self.leaderboard.print()
class Main:
    def __init__(self, driver, url):
        
        self.driver : webdriver.Chrome = driver
        self.driver.get(url)
        self.url = url
        self.db = DB('login.json')

        self.tasks = []
        self.olymps = dict()

        self.login : str
        self.password : str
        self.load_user_data()
    
        self.apply()

        print("\n".join(self.get_olymps()))
        self.choose_olymp("olympiad_195")#input("olymp id > "))

        self.get_tasks()

    def load_user_data(self):
        self.login = self.db.read("login")
        self.password = self.db.read("password")        
        if (self.login == "ERROR"):
            self.db.write('login', input("login > "))
            self.load_user_data()
        if (self.password == "ERROR"):
            self.db.write('password', input("password > "))
            self.load_user_data()

    def apply(self):
        sleep(4)
        form = self.driver.find_element(By.ID, "auth_form")

        email = form.find_elements(By.NAME, "email")
        email[0].send_keys(self.login)

        passw = form.find_elements(By.NAME, "password")
        passw[0].send_keys(self.password)

        form.submit()
        sleep(2)

    def get_olymps(self):
        res = self.driver.find_elements(By.TAG_NAME, 'a')[3:-1]
        for i in res:
            self.olymps[i.get_attribute("id")] = i
        return self.olymps
    
    def choose_olymp(self, ids):
        self.olymps[ids].click()
        sleep(3)

    def get_tasks(self):
        res = self.driver.find_elements(By.TAG_NAME, 'a')[5:-1]
        for i in res:
            name = "_".join(i.text.split()[:3])
            self.tasks.append(Pack(self.driver, i, name))

    def choose_tasks(self, idx):
        return self.tasks[idx]
    
if __name__ == "__main__":
    options = Options()
    #options.add_argument("--headless")
    options.add_experimental_option("detach", True)
    driver = webdriver.Chrome(options = options)
    m = Main(driver, 'https://fresh.nsuts.ru/nsuts-new/login')
    pack : Pack = m.choose_tasks(int(input("pack index > ")))
    pack.load()
    pack.load_file()
    pack.send_task(4)
    pack.get_leaderboard()
    
