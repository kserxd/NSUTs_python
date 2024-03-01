#!/usr/bin/env python3

import requests
import json, time, base64
from typing import Any, Dict, List, Tuple, Optional, NamedTuple, Union

class NsutsClient:
    def __init__(self, config = {}):
        # type: (Dict[str, Any]) -> None
        self.config = config

    # internal (TODO: start names of private methods with underscore)

    def __do_verify__(self):
        # type: () -> bool
        return self.config.get('verify', True)

    def __get_cookies__(self):
        # type: () -> Dict[str, str]
        return {
            'CGISESSID': self.config['session_id'],
            'PHPSESSID': self.config['session_id'],
        }

    def __request_get__(self, path):
        # type: (str) -> Any
        if path[0] != '/':
            path = '/' + path
        url = self.config['nsuts'] + path

        response = requests.get(url, cookies = self.__get_cookies__(), verify = self.__do_verify__())

        response.raise_for_status()
        return response

    def __request_post__(self, path, data, is_json = True):
        # type: (str, Dict[str, Any], bool) -> Any
        if path[0] != '/':
            path = '/' + path
        url = self.config['nsuts'] + path

        xcookies = self.__get_cookies__() if 'session_id' in self.config else None
        xdata = None if is_json else data
        xjson = data if is_json else None
        response = requests.post(url, data = xdata, json = xjson, cookies = xcookies, verify = self.__do_verify__())

        response.raise_for_status()
        return response

    def __get_state__(self):
        # type: () -> Any
        response = self.__request_get__('/api/config')
        state = response.json()

        have_url = self.config['nsuts'].rstrip('/')
        want_url = state['nsuts'].rstrip('/')
        assert have_url == want_url, "Unexpected server address in API config json: %s" % str(state)

        return state

    # public

    def is_authorized(self):
        # type: () -> bool
        return 'session_id' in self.config

    def auth(self):
        # type: () -> None
        data = {
            'email': self.config['email'],
            'password': self.config['password'],
            'method': 'internal',
        }
        response = self.__request_post__('/api/login', data)
        auth_result = response.json()

        assert auth_result['success'] == True, "Authorization error: %s" % auth_result['error']
        self.config['session_id'] = auth_result['sessid']

        assert self.__get_state__()['session_id'] == self.config['session_id'], "Session ID not saved"

    def get_olympiads(self):
        response = self.__request_get__('/api/olympiads/list').json()['registeredTo'];
        return response

    def get_tours(self):
        response = self.__request_get__('/api/tours/list').json()['tours'];
        return response


    def select_olympiad(self, olympiad_id):
        # type: (int) -> None
        data = {
            'olympiad': str(olympiad_id)
        }
        response = self.__request_post__('/api/olympiads/enter', data)

        now_olympiad = self.__get_state__()['olympiad_id']
        assert str(now_olympiad) == str(olympiad_id), "Failed to change olympiad ID: have %s instead of %s" % (str(now_olympiad), str(olympiad_id))

    def select_tour(self, tour_id):
        # type: (int) -> None
        response = self.__request_get__('/api/tours/enter?tour=' + str(tour_id))
        now_tour = self.__get_state__()['tour_id']
        assert str(now_tour) == str(tour_id), "Failed to change tour ID: have %s instead of %s" % (str(now_tour), str(tour_id))


    def get_tour_statement_id(self):
        response = self.__request_get__("/api/news/page_info")
        return response.json()['statements']['forTour'][0]['id']
    
    def download_tour_statement(self, path):
        response = self.__request_get__(f"/api/news/tour_statement?id={self.get_tour_statement_id()}")
        with open(f"{path}/statement.pdf", 'wb') as f:
            f.write(response.content)
        
    def get_tasks(self):
        response = self.__request_get__('/api/submit/submit_info').json()['tasks']
        return response

    def get_admin_queue(self, limit = 25, tasks = None):
        # type: (int, Optional[List[int]]) -> Any
        url = '/api/queue/submissions?limit=' + str(limit)
        if tasks is not None:
            url = url + '&task=' + ','.join(map(str, tasks))
        response = self.__request_get__(url)
        submits = json.loads(response.text)
        return submits
    
    def get_solution_source(self, solution_id):
        # type: (int) -> bytes
        url = '/api/submit/get_source?id=' + str(solution_id)
        response = self.__request_get__(url).json()
        if 'data' in response:  # zip archive for emailtester problems
            return {
                'type': 'emailtester',
                'content': base64.b64decode(response['data']),
            }
        else:
            return b''.join([base64.b64decode(line) for line in response['text']])

    def submit_solution(self, task_id, compiler_name, source_text):
        # type: (int, str, Union[bytes,str]) -> None
        data = {
            'langId': compiler_name,
            'taskId': task_id,
            'sourceText': source_text
        }
        response = self.__request_post__('/api/submit/do_submit', data, is_json = False)

    def get_my_last_submit_id(self):
        # type: () -> Optional[int]
        submits = self.get_my_submits_status()
        if len(submits) == 0:
            return None
        submits = sorted(submits, key = lambda s: s['date'])
        return int(submits[-1]['id'])

    def get_my_submits_status(self):
        # type: () -> Any
        response = self.__request_get__('/api/report/get_report')
        return json.loads(response.text)['submits']


RunResult = NamedTuple('RunResult', [('verdict', str), ('exit_code', int), ('time', float), ('memory', float)])
def nsuolymp_get_results(nsuts, submit_ids, submit_names, admin = False):
    # type: (NsutsClient, List[int], List[str], bool) -> Optional[List[Tuple[str, List[RunResult]]]]
    while True:
        nsuts_results = nsuts.get_my_submits_status()
        id_to_result = {int(res['id']):res for res in nsuts_results}

        all_ready = True
        out_results = []
        for i,sid in enumerate(submit_ids):
            if sid not in id_to_result.keys():
                return None
            res = id_to_result[sid]
            verdicts = res['result_line']
            if verdicts is None:
                all_ready = False
                break
            rr = [RunResult(ver, -1, -1.0, -1.0) for ver in verdicts]
            out_results.append((submit_names[i], rr))

        if all_ready:
            break
        time.sleep(1.0)

    if admin:
        #TODO: request only my own submits
        nsuts_adminres = nsuts.get_admin_queue(limit = 999)
        id_to_result = {int(res['id']):res for res in nsuts_adminres["submissions"]}

        out_results = []
        for i,sid in enumerate(submit_ids):
            assert(sid in id_to_result.keys())
            res = id_to_result[sid]
            verdicts = res['res']
            assert(verdicts is not None)
            tnm_json = res['time_and_memory']
            tnm = json.loads(tnm_json) if tnm_json is not None else None
            rr = []
            for t,ver in enumerate(verdicts):
                test_time = -1.0
                test_memory = -1.0
                if tnm is not None:
                    key = str(t+1)
                    test_time = float(tnm[key]["t"]) * 0.001
                    test_memory = float(tnm[key]["m"])
                rr.append(RunResult(ver, -1, test_time, test_memory))
            out_results.append((submit_names[i], rr))

    return out_results


def main():
    # type: () -> None
    config = {
        # URL is required field in this config
        'nsuts': 'http://10.0.3.162/nsuts-new',

        # There two ways for authentication in NsuTS
        # 1. Specify email and password
        'email': 'test@test.ru',
        'password': 'test',
        # 2. Specify sessid, which will be assigned after successful authenticaion
        #'session_id': 'cbc5750b24f9b17e3fc77a22fa941a1d',

        # Olympid ID and and Tour ID are not using by default, these lines can be omitted
        'olympiad_id': 58,
        'tour_id': 11114
    } # type: Any

    nsuts = NsutsClient(config)
    if not nsuts.is_authorized():
        nsuts.auth()
    #print(nsuts.config['session_id'])
    nsuts.select_olympiad(config['olympiad_id'])
    nsuts.select_tour(config['tour_id'])
    #nsuts.get_admin_queue()
    #source_text = nsuts.get_solution_source(311692)
    #nsuts.submit_solution(117795, 'vcc2015', source_text)
    print(nsuts.get_my_submits_status())
    print(nsuts.get_my_last_submit_id())

if __name__ == '__main__':
    main()