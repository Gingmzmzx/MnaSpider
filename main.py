import requests
import hashlib
import re
from bs4 import BeautifulSoup
from markdownify import markdownify as md



_mna_username = "changeit"
_mna_password = "changeit"
_akioioj_username = "changeit"
_akioioj_password = "changeit"
_debug = False


class NotLoginError(Exception): pass
class RequestError(Exception): pass
class ParseError(Exception): pass


class VijosSpider:
    def __init__(self):
        self.password = None
        self.username = None
        self.url = 'https://oj.xzynb.top'
        self.csrf_token: str = ""
        self.session = requests.Session()
        self.session.headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'zh-CN,zh;q=0.9',
            'cache-control': 'no-cache',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://oj.xzynb.top',
            'pragma': 'no-cache',
            'priority': 'u=0, i',
            'referer': 'https://oj.xzynb.top/',
            'sec-ch-ua': '"Not)A;Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
        }

        # Send init request
        self.session.get(self.url)
        print("Init request success, sid: ", self.session.cookies.get('sid'))

    def getCsrfToken(self, script_content):
        # 使用正则表达式匹配 csrf_token
        match = re.search(r'"csrf_token"\s*:\s*"([a-f0-9]{64})"', script_content)

        if match:
            csrf_token = match.group(1)
            return csrf_token
        else:
            raise ParseError("解析失败！")

    def login(self, username: str, password: str):
        self.username = username
        self.password = password
        data = self.session.post(self.url+"/login", data={
            "uname": self.username,
            "password": self.password,
        })
        print("Request login: ", data.status_code)
        if data.status_code != 200:
            raise RequestError("请求失败！")
        self.csrf_token = self.getCsrfToken(data.text)
        return data.text

    def createProblem(self, title: str, content: str, numeric_pid: bool = True, domain_id: str = None):
        data = {
            'title': title,
            'numeric_pid': "on" if numeric_pid else "off",
            'content': content,
            'csrf_token': self.csrf_token,
        }
        url = self.url
        if domain_id:
            url += f"/d/{domain_id}/p/create"
        else:
            url += "/p/create"
        response = self.session.post(url, data=data)
        print(f"Create Problem: {title}", response.status_code)



class MnaSpider:
    def __init__(self):
        self.password = None
        self.username = None
        self.url = 'https://mna.wang'
        self.session = requests.Session()
        self.session.headers = {
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Origin': 'https://mna.wang',
            'Pragma': 'no-cache',
            'Referer': 'https://mna.wang/login?url=%2F',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest',
            'sec-ch-ua': '"Not)A;Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }

        # Send init request
        self.session.get(self.url)
        print("Init request success, connect.sid: ", self.session.cookies.get('connect.sid'))

    def actLogin(self):
        password = self.password + "syzoj2_xxx"
        passwd: str = hashlib.md5(password.encode()).hexdigest()

        data = self.session.post(self.url+"/api/login", data={
            'username': self.username,
            'password': passwd,
        })

        print("Request login: ", data.status_code)
        return data.json()

    def handleLogin(self, data: dict) -> bool:
        if data['error_code'] == 1:
            print("Login success!")
            return True
        elif data['error_code'] == 1001:
            print("用户不存在！")
        elif data['error_code'] == 1002:
            print("密码错误")
        elif data['error_code'] == 1003:
            print("您尚未设置密码，请通过下方「找回密码」来设置您的密码。")
        return False

    def login(self, username: str, password: str):
        self.username = username
        self.password = password
        login_data = self.actLogin()
        if not self.handleLogin(login_data):
            raise NotLoginError("登录失败！")

    def parseHtml(self, html: str):
        soup = BeautifulSoup(html, 'html.parser')
        return soup

    def getProblem(self, problem_id: int, contest_id: int = None):
        url = self.url
        if contest_id:
            url += f"/contest/{contest_id}"
        url += f"/problem/{problem_id}"

        data = self.session.get(url)
        if data.status_code != 200:
            raise RequestError("请求失败！")
        try:
            soup = self.parseHtml(data.text)
            header = soup.find('h1', class_='ui header')
            if not header:
                title = "Unknown"
            else:
                title = header.text.strip()
            grid = soup.find('div', class_='ui grid')
            ret: str = ""
            for child in grid.children:
                item = self.parseHtml(str(child))
                child = item.find('div', class_='column')
                if not child:
                    continue
                string = str(child)
                if "ui top attached block header" not in string:
                    continue
                ret += md(string)
            return title, ret.strip()
        except Exception as e:
            if _debug:
                with open(f"logs/problems/{problem_id}_{contest_id}.html", "w", encoding="utf-8") as f:
                    f.write(data.text)
            raise RequestError("获取失败，可能是题目不存在或比赛未报名") from e

    def getContest(self, contest_id: int):
        url = self.url + f"/contest/{contest_id}"
        data = self.session.get(url)
        if data.status_code != 200:
            raise RequestError("请求失败！")
        try:
            soup = self.parseHtml(data.text)
            header = soup.find('div', class_='padding')
            if not header:
                raise RequestError("获取失败，可能是比赛不存在或未报名")
            title_dom = header.find('h1')
            title = title_dom.text.strip()
            announcement_dom = soup.find('div', class_='ui bottom attached segment font-content')
            if announcement_dom:
                announcement = announcement_dom.text.strip()
            else:
                announcement = ""
            tbody = soup.find('tbody')
            p_list: list = []
            for i in tbody.children:
                if i.text.strip():
                    p_list.append(i.text.strip())
            return title, announcement, p_list
        except Exception as e:
            if _debug:
                with open(f"logs/contests/{contest_id}.html", "w", encoding="utf-8") as f:
                    f.write(data.text)
            raise RequestError("获取失败，可能是比赛不存在或未报名") from e


def copySingleProblem():
    mna_spider = MnaSpider()
    mna_spider.login(_mna_username, _mna_password)
    problem = mna_spider.getProblem(1, contest_id=1330)

    title = re.sub(r"#\d+\.\s*", "", problem[0])
    content = problem[1]

    vijos_spider = VijosSpider()
    vijos_spider.login(_akioioj_username, _akioioj_password)
    vijos_spider.createProblem(title, content, domain_id="mxoj")

def copyProblemsFromContest():
    mna_spider = MnaSpider()
    mna_spider.login(_mna_username, _mna_password)
    vijos_spider = VijosSpider()
    vijos_spider.login(_akioioj_username, _akioioj_password)

    # Copy Problems
    _start_id = 1063
    _end_id = 1112
    problem_list: dict = {}
    i: int = _end_id
    while i >= _start_id:
        try:
            contest = mna_spider.getContest(i)
            cnt = len(contest[2])
            contest_title = contest[0]
        except RequestError as e:
            print(f"获取比赛失败！Contest: {i}")
            i -= 1
            continue
        for l in range(1, cnt+1):
            try:
                problem = mna_spider.getProblem(l, contest_id=i)
                title = re.sub(r"#\d+\.\s*", "", problem[0])
                content = problem[1]
                if title in problem_list:
                    print(f"题目已存在！Contest: {i}, Problem: {l}")
                    continue
                print("Copying: ", title, "Contest: ", i, "Problem: ", l)
                problem_list[title] = content
                vijos_spider.createProblem(f"【{contest_title}】{title}", content, domain_id="mxoj")
            except RequestError as e:
                raise Exception(f"复制题目失败！Contest: {i}, Problem: {l}") from e
        i -= 1

if __name__ == '__main__':
    mna_spider = MnaSpider()
    mna_spider.login(_mna_username, _mna_password)
    vijos_spider = VijosSpider()
    vijos_spider.login(_akioioj_username, _akioioj_password)

