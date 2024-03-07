#!/usr/bin/env python3

import requests
import json, time, base64
from typing import Any, Dict, List, Tuple, Optional, NamedTuple, Union


class NsutsClient:
    def __init__(self, config={}):
        # type: (Dict[str, Any]) -> None
        self.config = config

    # internal

    def __do_verify__(self) -> bool:
        return self.config.get("verify", True)

    def __get_cookies__(self) ->  Dict[str, str]:
        return {
            "CGISESSID": self.config["session_id"],
            "PHPSESSID": self.config["session_id"],
        }

    def __get_state__(self) -> Dict[str, Any]:
        response = self.__request_get__("/api/config")
        state = response.json()

        have_url = self.config["nsuts"].rstrip("/")
        want_url = state["nsuts"].rstrip("/")
        assert (
            have_url == want_url
        ), "Unexpected server address in API config json: %s" % str(state)

        return state

    def __request_get__(self, path: str) -> requests.Response | None:
        # type: (str) -> Any
        if path[0] != "/":
            path = "/" + path
        url = self.config["nsuts"] + path

        response = requests.get(
            url, cookies=self.__get_cookies__(), verify=self.__do_verify__()
        )

        response.raise_for_status()
        return response

    def __request_post__(self, path: str, data: Dict[str, Any], files: Dict[str, Any] = None, is_json: bool = True) -> requests.Response:
        if path[0] != "/":
            path = "/" + path
        url = self.config["nsuts"] + path

        xcookies = self.__get_cookies__() if "session_id" in self.config else None
        xdata = None if is_json else data
        xjson = data if is_json else None
        response = requests.post(
            url,
            data=xdata,
            files=files,
            json=xjson,
            cookies=xcookies,
            verify=self.__do_verify__(),
        )

        response.raise_for_status()
        return response

    # public

    # Auth
    def auth(self) -> None:
        data = {
            "email": self.config["email"],
            "password": self.config["password"],
            "method": "internal",
        }
        response = self.__request_post__("/api/login", data)
        auth_result = response.json()

        assert auth_result["success"] == True, (
            "Authorization error: %s" % auth_result["error"]
        )
        self.config["session_id"] = auth_result["sessid"]

        assert (
            self.__get_state__()["session_id"] == self.config["session_id"]
        ), "Session ID not saved"

    def is_authorized(self) -> bool:
        return "session_id" in self.config

    # Get requests
    def download_task(self, ids: int) -> List[str] | None:
        if ids != -1:
            data = {
                i["task_id"]: i["id"]
                for i in self.get_reports()
                if i["result_line"][-1] == "A"
            }
            submit_id = ""
            try:
                submit_id = data[str(ids)]
            except:
                pass
            if submit_id:
                response = self.__request_get__(
                    f"/api/submit/get_source?id={submit_id}"
                ).json()
                if response["compiler"] == "emailtester":
                    return [response["data"], response["report"], response["compiler"]]
                else:
                    return [response["text"], response["compiler"]]
        return ""

    def download_tour_statement(self, path: str) -> None:
        tour_statement = self.__request_get__(
            f"/api/news/tour_statement?id={self.get_tour_statement_id()}"
        )
        with open(f"{path}/statement.pdf", "wb") as f: f.write(tour_statement.content)
    
    def get_compilators(self) -> Dict[str, str]:
        return self.__request_get__("/api/submit/submit_info").json()["langs"]

    def get_my_last_submit_id(self) -> int | None:
        submits = self.get_my_submits_status()
        if len(submits) == 0:
            return None
        submits = sorted(submits, key=lambda s: s["date"])
        return int(submits[-1]["id"])

    def get_my_last_submit(self) -> int | None:
        submits = self.get_my_submits_status()
        if len(submits) == 0:
            return None
        submits = sorted(submits, key=lambda s: s["date"])
        return submits[-1]

    def get_my_submits_status(self) -> List[Dict[str, str | int]]:
        response = self.__request_get__("/api/report/get_report").json()
        return response["submits"]

    def get_olympiads(self) -> List[Dict[str, str | int]]:
        response = self.__request_get__("/api/olympiads/list").json()["registeredTo"]
        return response

    def get_olympiad_id_by_name(self, name: str) -> str | int | None:
        for i in self.get_olympiads():
            if i["title"].replace(" ", "_").replace("(", "").replace(")", "") == name:
                return i["id"]
        return None

    def get_olympiad_name_by_id(self, ids):
        for i in self.get_olympiads():
            if i["id"] == ids:
                return i["title"]
        return -1

    def get_points(self, ids):
        return self.__request_get__(
            "/api/plugins/students/submit_points?id=" + str(ids)
        ).json()["points"]

    def get_reports(self):
        response = self.__request_get__("/api/report/get_report").json()["submits"]
        return response
 
    def get_result(self):
        return self.get_my_last_submit()["result_line"]

    def get_solution_source(self, solution_id):
        # type: (int) -> bytes
        url = "/api/submit/get_source?id=" + str(solution_id)
        response = self.__request_get__(url).json()
        if "data" in response:  # zip archive for emailtester problems
            return {
                "type": "emailtester",
                "content": base64.b64decode(response["data"]),
                "result": base64.b64decode(response["report"]),
            }
        else:
            return b"".join([base64.b64decode(line) for line in response["text"]])

    def get_tours(self):
        response = self.__request_get__("/api/tours/list").json()["tours"]
        return response

    def get_tour_id_by_name(self, name):
        for i in self.get_tours():
            if i["title"].replace(" ", "_").replace("(", "").replace(")", "") == name:
                return i["id"]
        return -1

    def get_tour_name_by_id(self, ids):
        for i in self.get_tours():
            if i["id"] == ids:
                return i["title"]
        return -1

    def get_tour_statement_id(self):
        response = self.__request_get__("/api/news/page_info")
        return response.json()["statements"]["forTour"][0]["id"]

    def get_tasks(self):
        response = self.__request_get__("/api/submit/submit_info").json()["tasks"]
        return response

    def get_task_id_by_name(self, name):
        for i in self.get_tasks():
            if i["title"].replace(" ", "_").replace("(", "").replace(")", "") == name:
                return int(i["id"])
        return -1

    # Post requests
    def select_olympiad(self, olympiad_id):
        # type: (int) -> None
        data = {"olympiad": str(olympiad_id)}
        response = self.__request_post__("/api/olympiads/enter", data)

        now_olympiad = self.__get_state__()["olympiad_id"]
        assert str(now_olympiad) == str(
            olympiad_id
        ), "Failed to change olympiad ID: have %s instead of %s" % (
            str(now_olympiad),
            str(olympiad_id),
        )

    def select_tour(self, tour_id):
        # type: (int) -> None
        response = self.__request_get__("/api/tours/enter?tour=" + str(tour_id))
        now_tour = self.__get_state__()["tour_id"]
        assert str(now_tour) == str(
            tour_id
        ), "Failed to change tour ID: have %s instead of %s" % (
            str(now_tour),
            str(tour_id),
        )

    def submit_solution(self, task_id, compiler_name, source_text):
        # type: (int, str, Union[bytes,str]) -> None
        data = {"langId": compiler_name, "taskId": task_id, "sourceText": ""}
        files = {"sourceFile": ""}
        if compiler_name == "emailtester":
            files["sourceFile"] = open(source_text, "rb")
        else:
            data["sourceText"] = source_text
        response = self.__request_post__(
            "/api/submit/do_submit", data, files, is_json=False
        )
        return response

