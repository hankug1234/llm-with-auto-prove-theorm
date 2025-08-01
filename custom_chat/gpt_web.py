import time, os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common import TimeoutException
# === 설정 ===
from config import DEBUG_PORT, CHROMEDRIVER_PATH
import socket
from pathlib import Path
import subprocess, socket, tempfile, time

class ChatGPTWeb:
    
    def __init__(self,model:str="gpt-4o"):
        self.assistant_sel = "div[data-message-author-role='assistant']"
        self.input_sel     = "div#prompt-textarea.ProseMirror[contenteditable='true']"
        self.plus_btn_sel  = "button[data-testid='composer-plus-btn']"
        self.file_sel      = "input[type='file']"
        self.send_btnsel   = "button[data-testid='send-button']"
        self._launch_chrom_debug_linux()
        self.driver, self.wait = self._connect_driver()
        self.driver.get(f"https://chatgpt.com/?model={model}")
        self.wait.until(lambda d: 'chatgpt.com' in d.current_url)
        
    def __del__(self):
        subprocess.call(["pkill", "-f", "chrome"])
    
    def _launch_chrom_debug_linux(self):
        # 1) 기존 크롬 완전 종료
        subprocess.call(["pkill", "-f", "chrome"])

        # 2) 디버깅 모드 크롬 실행
        
        # ▶ 기본 프로필 대신 임시 전용 프로필 디렉터리 사용
        debug_profile = Path(tempfile.gettempdir()) / "chrome_debug_profile"
        debug_profile.mkdir(exist_ok=True)

        args = [
            "google-chrome",
            f"--remote-debugging-port={DEBUG_PORT}",
            f"--user-data-dir={debug_profile}",         # ★ 필수
            "--profile-directory=Default",
            "--remote-allow-origins=*",
            "--no-first-run", "--no-default-browser-check"
        ]
        subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 포트 열릴 때까지 최대 10초 대기
        for _ in range(20):
            try:
                with socket.create_connection(("127.0.0.1", DEBUG_PORT), timeout=0.5):
                    return
            except OSError:
                time.sleep(0.5)
        raise RuntimeError("DevTools 포트가 열리지 않았습니다.")

    def _launch_chrome_debug_window(self):
        chrome_path = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
        if not chrome_path.exists():
            chrome_path = Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe")

        # ▶ 기본 프로필 대신 임시 전용 프로필 디렉터리 사용
        debug_profile = Path(tempfile.gettempdir()) / "chrome_debug_profile"
        debug_profile.mkdir(exist_ok=True)

        args = [
            str(chrome_path),
            f"--remote-debugging-port={DEBUG_PORT}",
            f"--user-data-dir={debug_profile}",         # ★ 필수
            "--profile-directory=Default",
            "--remote-allow-origins=*",
            "--no-first-run", "--no-default-browser-check"
        ]
        subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 포트 열릴 때까지 최대 10초 대기
        for _ in range(20):
            try:
                with socket.create_connection(("127.0.0.1", DEBUG_PORT), timeout=0.5):
                    return
            except OSError:
                time.sleep(0.5)
        raise RuntimeError("DevTools 포트가 열리지 않았습니다.")


    def _scroll_to_bottom(self,driver):
        driver.execute_script("""
            const box = document.querySelector(
                'div.flex.h-full.flex-col.overflow-y-auto');
            if (box) box.scrollTop = box.scrollHeight;
        """)

    def _clear_file_input(driver):
        """
        ChatGPT composer 에 들어있는 <input type=file>의 '선택된 파일'을 지운다.
        1) value = '' 으로 초기화 시도
        2) 실패하면 새 input 으로 교체
        3) 이미 첨부돼 보이는 썸네일이 있으면 '제거' 버튼 클릭
        """
        driver.execute_script("""
        const composer = document.querySelector('#thread-bottom form');
        if (!composer) return;

        // ---- 0) 썸네일 제거 버튼 클릭 ---------------------------------
        composer.querySelectorAll(
            "button[aria-label^='Remove'],button[aria-label*='제거']"
        ).forEach(btn => btn.click());

        const oldInput = composer.querySelector("input[type=file]");
        if (!oldInput) return;

        // ---- 1) 값 비우기 시도 ----------------------------------------
        try {
            oldInput.value = '';           // 크롬이 허용하면 여기서 종료
            if (!oldInput.value) return;   // value가 비었으면 성공
        } catch (e) { /* ignore */ }

        // ---- 2) 복제본으로 교체 ---------------------------------------
        const fresh = oldInput.cloneNode(true); // 모든 속성 유지
        oldInput.parentNode.replaceChild(fresh, oldInput);
        """)

    def _connect_driver(self):
        options = Options()
        # 실행 중인 크롬 인스턴스에 붙기
        options.add_experimental_option("debuggerAddress", f"127.0.0.1:{DEBUG_PORT}")
        service = Service(CHROMEDRIVER_PATH) if CHROMEDRIVER_PATH else Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        wait = WebDriverWait(driver, 30)
        return driver, wait

    def _wait_until_static(self,driver, timeout=120, idle_sec=2, poll=0.4):
        """
        assistant 카드가 idle_sec 동안 변하지 않으면 완료.
        card 엘리먼트가 교체·삭제돼도 안전하게 재탐색.
        """
        first_card = driver.find_elements(By.CSS_SELECTOR, self.assistant_sel)[-1]
        msg_id   = first_card.get_attribute("data-message-id") or ""
        selector = f"[data-message-id='{msg_id}']" if msg_id else self.assistant_sel

        last_len      = -1
        stable_since  = time.time()
        deadline      = time.time() + timeout

        while time.time() < deadline:
            # ── ① 카드 엘리먼트 다시 얻기 ──────────────────────────
            try:
                card = driver.find_element(By.CSS_SELECTOR, selector)
            except Exception:
                # placeholder 가 교체되면 id 가 달라지므로
                cards = driver.find_elements(By.CSS_SELECTOR, self.assistant_sel)
                if not cards:                    # 아직 아무것도 없다면 ↺
                    time.sleep(poll)
                    continue
                card     = cards[-1]             # 가장 마지막 assistant
                selector = self.assistant_sel            # 다음 loop 부턴 이 셀렉터

            # ── ② 스크롤 & 길이 측정 ───────────────────────────────
            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});", card
            )
            cur_len = driver.execute_script(
                "return arguments[0].innerText.length;", card
            )

            # ── ③ idle 판정 ───────────────────────────────────────
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", card)
            if cur_len != last_len:
                last_len     = cur_len
                stable_since = time.time()
            elif time.time() - stable_since >= idle_sec:
                return card                      # ✅  스트리밍 끝!
            
            time.sleep(poll)
            
        # ── ④ 타임아웃 ───────────────────────────────────────────
        raise TimeoutException("assistant reply not finished in time")

    def invoke(self, text: str, image_path: str | None = None) -> dict:
        """텍스트/이미지 전송 후 응답 반환 (ProseMirror 입력 대응)"""
        driver = self.driver 
        wait = self.wait
        prev = len(driver.find_elements(By.CSS_SELECTOR, self.assistant_sel))
        inp = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, self.input_sel)))
        inp.click()
        ActionChains(driver).send_keys(text).perform()
        
        if image_path:
            # plus 버튼이 가려져 있을 수 있으므로 시도
            try:
                plus_btn = driver.find_element(By.CSS_SELECTOR, self.plus_btn_sel)
                plus_btn.click()

            except Exception:
                pass  # 이미 열려 있으면 무시
            
            self._clear_file_input(driver)    
            file_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, self.file_sel)))
            file_input.send_keys(os.path.abspath(image_path))
            time.sleep(3)  # 썸네일 로드 대기 (간단히)
        
        ActionChains(driver).send_keys(Keys.ENTER).perform()
        
        
        # ② Enter 키 이벤트를 강제로 디스패치  ▶ ProseMirror 가 ‘전송’ 으로 인식
        time.sleep(3)  # UI 가 버튼을 활성화할 시간
        try:
            send_btn = driver.find_element(By.CSS_SELECTOR, self.send_btnsel)
            if send_btn.is_enabled():
                send_btn.click()
        except Exception:
            pass 

        # ③ 새 assistant 턴 등장 대기
        
        wait_long = WebDriverWait(driver, 30)
        
        def _is_placeholder(card):
            mid = card.get_attribute("data-message-id") or ""
            return mid.startswith("placeholder")

        def _ready(driver):
            self._scroll_to_bottom(driver)                 # ← 가상 스크롤 해제
            cards = driver.find_elements(By.CSS_SELECTOR, self.assistant_sel)
            
            if len(cards) <= prev:
                return False

            last = cards[-1]
            if _is_placeholder(last):
                return False                      # 아직 진짜 카드 아님

            # 진짜 카드 등장!
            driver.execute_script(
                "arguments[0].scrollIntoView({block:'nearest'});", last)
            return True
        
        wait_long.until(_ready) 

        
        self._wait_until_static(driver) 
        reply = driver.find_elements(By.CSS_SELECTOR, self.assistant_sel)[-1]
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", reply)
        return reply.text
    