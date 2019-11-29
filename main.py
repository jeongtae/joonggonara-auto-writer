from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.expected_conditions import presence_of_element_located as PresenceOfElementLocated, element_to_be_clickable as ElementToBeClickable
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchWindowException, TimeoutException
from urllib.parse import urlencode, urlparse
from time import sleep
from os import chdir, listdir, path
#from html import escape as htmlescape

# URLs
writepageurl = 'https://cafe.naver.com/ArticleWrite.nhn?clubid=10050146&m=write'
#loginpageurl = 'https://nid.naver.com/nidlogin.login'
#loginpageurl += '?' + urlencode({'mode':'number' if onetimelogin else 'form', 'url':writepageurl})

# Default Options
usewatermark = False
useescro = True
useotn = True
fontsize = 18
homepath = '~/Desktop'

with Chrome('./chromedriver') as driver:
    wait = WebDriverWait(driver, 10)
    longwait = WebDriverWait(driver, 600)

    while True:
        # 사용자를 로그인 시키고, 글쓰기 페이지로 이동하기
        driver.get(writepageurl)
        while driver.current_url != writepageurl:
            try:
                longwait.until(lambda d: urlparse(d.current_url).netloc != 'nid.naver.com')
            except (NoSuchWindowException, TimeoutException):
                exit()
            driver.get(writepageurl)

        # 쓰기 페이지의 로딩을 기다리기
        wait.until(PresenceOfElementLocated((By.CSS_SELECTOR, 'h3.bi')))

        # 사용자가 파일을 선택할 수 있게, 쓰기 페이지를 변조하기
        driver.execute_script("""
        document.querySelector('h3.bi').innerHTML = 
            '내용 채우기할 파일 선택 -> <input id="ju-file" type="file" accept=".txt"><pre id="ju-txt" style="visibility: collapse; height: 0px;"></pre>';
        document.getElementById('ju-file').onchange = e => { 
            var file = e.target.files[0];
            if (file.type == 'text/plain') {
                var reader = new FileReader();
                reader.readAsText(file,'UTF-8');
                reader.onload = re => {
                    var txt = re.target.result;
                    document.getElementById('ju-txt').innerHTML = txt;
                }
            } else {
                alert('텍스트 파일만 선택 가능합니다.');
            }
        };
        """)

        # 사용자가 프리셋 파일 선택하기를 기다리기
        try:
            longwait.until(lambda d: d.find_element_by_id('ju-txt').get_property('innerHTML') != '')
        except (NoSuchWindowException, TimeoutException):
            exit()

        # 프리셋 가져오기
        jutxtsplit = driver.find_element_by_id('ju-txt').get_property('innerHTML').split('\n')
        picspath, category, title, price = jutxtsplit[0], jutxtsplit[1], jutxtsplit[2], jutxtsplit[3]
        content = '\n'.join(jutxtsplit[4:])

        # 카테고리 변경하기
        Select(driver.find_element_by_css_selector('select#boardCategory')).select_by_visible_text(category)
        sleep(.5)
        driver.switch_to.alert.accept()

        # 내용 일부 채우기
        driver.find_element_by_css_selector('input#subject').send_keys(title)
        wait.until(PresenceOfElementLocated((By.CSS_SELECTOR, 'input#sale_cost'))).send_keys(price)

        # 안전거래 및 연락처 공개 설정하기
        driver.find_element_by_css_selector('input#sale_open_phone').click()
        if useotn:
            driver.find_element_by_css_selector('input#sale_otn_use').click()
        if useescro:
            driver.find_element_by_css_selector('input#pay_corp_N').click()
            driver.find_element_by_css_selector('input#sale_chk_agree').click()
        else:
            driver.find_element_by_css_selector('button#sale_direct').click()

        # 사진 업로드 창 열기
        if not usewatermark:
            driver.find_element_by_css_selector('input#sale_watermark').click()
        driver.find_element_by_css_selector('a.ico_pic').click()
        driver.switch_to.window(driver.window_handles[-1])
        sleep(.5)
        wait.until(ElementToBeClickable((By.CSS_SELECTOR, 'button.npe_alert_btn_close'))).click()

        # 업로드할 사진 목록 준비하기
        homepath = path.expanduser(homepath)
        chdir(homepath)
        picpaths = listdir(picspath)
        picpaths = list(filter(lambda f: str.upper(f.split('.')[-1]) in ['JPEG', 'JPG', 'PNG'], picpaths))
        picpaths.sort()
        picpaths = list(map(lambda f: path.join(homepath, picspath, f), picpaths))
        
        # 사진 업로드하기
        driver.find_element_by_css_selector('input#pc_image_file').send_keys('\n'.join(picpaths))
        longwait.until(lambda d: not driver.find_element_by_css_selector('div.npe_alert').is_displayed())

        # 사진크기 설정을 변경하고 올리기 버튼을 눌러서 업로드 완료하기
        driver.find_element_by_class_name('npu_size_select').click()
        driver.find_element_by_css_selector(".npu_size_item[data-resize='original']").click()
        sleep(.5)
        driver.find_element_by_class_name('npu_btn_submit').click()
        longwait.until(lambda d: len(d.window_handles) == 1)
        driver.switch_to.window(driver.window_handles[0])

        # 글내용 덧붙이기
        driver.switch_to.frame(driver.find_element_by_css_selector('table#toolbox iframe'))
        #content = htmlescape(content)
        content = content.replace('\n', '<br>')
        content = content.replace('\'', '\\\'')
        content = content.replace('\\', '\\\\')
        driver.execute_script("""
        var node = document.createElement("span");
        node.innerHTML = '<br>"""+content+"""';
        node.style.fontSize = """+str(fontsize)+""";
        document.body.appendChild(node);
        """)
        driver.switch_to.parent_frame()

        # 글쓰기 완료를 기다리기
        longwait.until(lambda d: urlparse(d.current_url).path != urlparse(writepageurl).path)
