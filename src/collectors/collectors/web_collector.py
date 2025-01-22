"""Module for Web collector."""

import copy
import datetime
import hashlib
import os
import re
import selenium
import subprocess
import time
import uuid
from .base_collector import BaseCollector
from dateutil.parser import parse
from managers.log_manager import logger
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from shared.config_collector import ConfigCollector
from shared.schema.news_item import NewsItemData, NewsItemAttribute
from urllib.parse import urlparse


class WebCollector(BaseCollector):
    """Collector for gathering data from web page.

    Attributes:
        type (str): The type of the collector.
        name (str): The name of the collector.
        description (str): The description of the collector.
        parameters (list): The list of parameters for the collector.
        auth_username (str): The username for web page authentication.
        auth_password (str): The password for web page authentication.
        web_url (str): The URL of the web page.
        interpret_as (str): The type of the URL (uri or directory).
        user_agent (str): The user agent for the web page.
        tor_service (str): The Tor service status.
        pagination_limit (int): The maximum number of pages to visit.
        links_limit (int): The maximum number of article links to process.
        word_limit (int): The limit for the article body.
        selectors (dict): The dictionary of selectors for the web page.
        web_driver_type (str): The type of the web driver.
        client_cert_directory (str): The directory with client's certificates.
        proxy (str): The proxy server.
        proxy_port (int): The proxy port.
        proxy_proto (str): The proxy protocol.
        proxy_host (str): The proxy
    """

    type = "WEB_COLLECTOR"
    config = ConfigCollector().get_config_by_type(type)
    name = config.name
    description = config.description
    parameters = config.parameters
    logger.debug(f"Selenium version: {selenium.__version__}")

    @staticmethod
    def __get_prefix_and_selector(element_selector):
        """Extract the prefix and selector from the given element_selector.

        Parameters:
            element_selector (str): The element selector in the format "prefix: selector".
        Returns:
            tuple: A tuple containing the prefix and selector as separate strings.
        """
        selector_split = element_selector.split(":", 1)
        if len(selector_split) != 2:
            return "", ""
        prefix = selector_split[0].strip().lower()
        selector = selector_split[1].lstrip()
        return prefix, selector

    @staticmethod
    def __get_element_locator(element_selector):
        """Extract a single element from the headless browser by selector.

        Parameters:
            element_selector (str): The selector used to locate the element.
        Returns:
            locator (tuple): A tuple containing the locator type and the selector.
        """
        prefix, selector = WebCollector.__get_prefix_and_selector(element_selector)

        locator = None
        if prefix == "id":
            locator = (By.ID, selector)
        if prefix == "name":
            locator = (By.NAME, selector)
        elif prefix == "xpath":
            locator = (By.XPATH, selector)
        elif prefix in ["tag_name", "tag"]:
            locator = (By.TAG_NAME, selector)
        elif prefix in ["class_name", "class"]:
            locator = (By.CLASS_NAME, selector)
        elif prefix in ["css_selector", "css"]:
            locator = (By.CSS_SELECTOR, selector)

        return locator

    @staticmethod
    def __find_element_by(driver, element_selector):
        """Extract single element from the headless browser by selector.

        Parameters:
            driver: The headless browser driver.
            element_selector: The selector used to locate the element.
        Returns:
            The extracted element.
        """
        prefix, selector = WebCollector.__get_prefix_and_selector(element_selector)

        element = None
        if prefix == "id":
            element = driver.find_element(By.ID, selector)
        if prefix == "name":
            element = driver.find_element(By.NAME, selector)
        elif prefix == "xpath":
            element = driver.find_element(By.XPATH, selector)
        elif prefix in ["tag_name", "tag"]:
            element = driver.find_element(By.TAG_NAME, selector)
        elif prefix in ["class_name", "class"]:
            element = driver.find_element(By.CLASS_NAME, selector)
        elif prefix in ["css_selector", "css"]:
            element = driver.find_element(By.CSS_SELECTOR, selector)

        return element

    @staticmethod
    def __find_element_text_by(driver, element_selector, return_none=False):
        """Find the text of an element identified by the given selector using the provided driver.

        Parameters:
            driver: The driver object used to interact with the web page.
            element_selector: The selector used to locate the element.
            return_none (bool): A boolean indicating whether to return None if the element is not found.
                         If set to False, an empty string will be returned instead.
                         Defaults to False.
        Returns:
            The text of the element if found, otherwise None or an empty string based on the value of return_none.
        """
        if return_none:
            failure_retval = None
        else:
            failure_retval = ""

        try:
            ret = WebCollector.__find_element_by(driver, element_selector)
            if not ret:
                return failure_retval
            return ret.text
        except NoSuchElementException as e:  # noqa F841
            return failure_retval

    @staticmethod
    def __find_elements_by(driver, element_selector):
        """Extract list of elements from the headless browser by selector.

        Parameters:
            driver: The headless browser driver.
            element_selector: The selector used to locate the elements.
        Returns:
            A list of elements found using the given selector.
        """
        prefix, selector = WebCollector.__get_prefix_and_selector(element_selector)
        # logger.debug(f"Prefix: {prefix}")
        # logger.debug(f"Selector: {selector}")
        # logger.debug(f"Page source code: {driver.page_source}")

        elements = None
        if prefix == "id":
            elements = [driver.find_element(By.ID, selector)]
        if prefix == "name":
            elements = driver.find_elements(By.NAME, selector)
        elif prefix == "xpath":
            elements = driver.find_elements(By.XPATH, selector)
        elif prefix in ["tag_name", "tag"]:
            elements = driver.find_elements(By.TAG_NAME, selector)
        elif prefix in ["class_name", "class"]:
            elements = driver.find_elements(By.CLASS_NAME, selector)
        elif prefix in ["css_selector", "css"]:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
        return elements

    @staticmethod
    def __safe_find_elements_by(driver, element_selector):
        """Safely find elements by the given element selector using the provided driver.

        Parameters:
            driver: The driver object used to interact with the web page.
            element_selector: The selector used to locate the elements.
        Returns:
            A list of elements matching the given selector, or None if no elements are found.
        """
        try:
            ret = WebCollector.__find_elements_by(driver, element_selector)
            if not ret:
                return None
            return ret
        except NoSuchElementException as e:  # noqa F841
            return None

    @staticmethod
    def __smart_truncate(content, length=500, suffix="..."):
        """Truncate the given content to a specified length and adds a suffix if necessary.

        Parameters:
            content (str): The content to be truncated.
            length (int): The maximum length of the truncated content. Default is 500.
            suffix (str): The suffix to be added at the end of the truncated content. Default is "...".
        Returns:
            (str): The truncated content.
        """
        if len(content) <= length:
            return content
        else:
            return " ".join(re.compile(r"\s+").split(content[: length + 1])[0:-1]) + suffix

    @staticmethod
    def __wait_for_new_tab(browser, timeout, current_tab):
        """Wait for a new tab to open in the browser.

        Parameters:
            browser (WebDriver): The browser instance.
            timeout (int): The maximum time to wait for a new tab to open, in seconds.
            current_tab (str): The current tab handle.
        Raises:
            TimeoutException: If a new tab does not open within the specified timeout.
        """
        yield
        WebDriverWait(browser, timeout).until(lambda browser: len(browser.window_handles) != 1)
        for tab in browser.window_handles:
            if tab != current_tab:
                browser.switch_to.window(tab)
                return

    def __close_other_tabs(self, browser, handle_to_keep, fallback_url):
        """Close all browser tabs except for the specified handle.

        Parameters:
            browser (WebDriver): The browser instance.
            handle_to_keep (str): The handle of the tab to keep open.
            fallback_url (str): The URL to load if tab restoration fails.
        Returns:
            (bool): True if the tab restoration is successful and the current window handle matches the handle_to_keep, False otherwise.
        """
        try:
            handles_to_close = copy.copy(browser.window_handles)
            for handle_to_close in handles_to_close:
                if handle_to_close != handle_to_keep:
                    browser.switch_to.window(handle_to_close)
                    browser.close()
                    # time.sleep(1)
                if len(browser.window_handles) == 1:
                    break
            browser.switch_to.window(handle_to_keep)
        except Exception as error:
            logger.exception(f"{self.collector_source} Browser tab restoration failed, reloading the title page: {error}")
            try:
                # last resort - at least try to reopen the original page
                browser.get(fallback_url)
                return True
            except Exception as error:
                logger.exception(f"{self.collector_source} Fallback to the original page failed: {error}")
                return False
        return browser.current_window_handle == handle_to_keep

    def __parse_settings(self):
        """Load the collector settings to instance variables.

        Returns:
            bool: True if the settings were successfully loaded, False otherwise.
        """
        self.auth_username = self.source.parameter_values["AUTH_USERNAME"]
        self.auth_password = self.source.parameter_values["AUTH_PASSWORD"]

        # parse the URL
        web_url = self.source.parameter_values["WEB_URL"]

        if web_url.lower().startswith("file://"):
            file_part = web_url[7:]
            if os.path.isfile(file_part):
                self.interpret_as = "uri"
                self.web_url = "file://" + file_part
            elif os.path.isdir(file_part):
                self.interpret_as = "directory"
                self.web_url = file_part
            else:
                logger.warning(f"{self.collector_source} Missing file {web_url}")
                return False

        elif re.search(r"^[a-z0-9]+://", web_url.lower()):
            self.interpret_as = "uri"
            self.web_url = web_url
        elif os.path.isfile(web_url):
            self.interpret_as = "uri"
            self.web_url = f"file://{web_url}"
        elif os.path.isdir(web_url):
            self.interpret_as = "directory"
            self.web_url = web_url
        else:
            self.interpret_as = "uri"
            self.web_url = f"https://{web_url}"

        if self.interpret_as == "uri" and self.auth_username and self.auth_password:
            parsed_url = urlparse(self.web_url)
            self.web_url = f"{parsed_url.scheme}://{self.auth_username}:{self.auth_password}@{parsed_url.netloc}{parsed_url.path}"

        # parse other arguments
        self.user_agent = self.source.parameter_values["USER_AGENT"]
        self.tor_service = self.source.parameter_values["TOR"]

        # self.interval = self.source.parameter_values['REFRESH_INTERVAL']

        self.pagination_limit = BaseCollector.read_int_parameter("PAGINATION_LIMIT", 1, self.source)
        self.links_limit = BaseCollector.read_int_parameter("LINKS_LIMIT", 0, self.source)
        self.word_limit = BaseCollector.read_int_parameter("WORD_LIMIT", 0, self.source)

        self.selectors = {}

        self.selectors["popup_close"] = self.source.parameter_values["POPUP_CLOSE_SELECTOR"]
        self.selectors["next_page"] = self.source.parameter_values["NEXT_BUTTON_SELECTOR"]
        self.selectors["load_more"] = self.source.parameter_values["LOAD_MORE_BUTTON_SELECTOR"]
        self.selectors["single_article_link"] = self.source.parameter_values["SINGLE_ARTICLE_LINK_SELECTOR"]

        self.selectors["title"] = self.source.parameter_values["TITLE_SELECTOR"]
        self.selectors["article_description"] = self.source.parameter_values["ARTICLE_DESCRIPTION_SELECTOR"]
        self.selectors["article_full_text"] = self.source.parameter_values["ARTICLE_FULL_TEXT_SELECTOR"]
        self.selectors["published"] = self.source.parameter_values["PUBLISHED_SELECTOR"]
        self.selectors["author"] = self.source.parameter_values["AUTHOR_SELECTOR"]
        self.selectors["attachment"] = self.source.parameter_values["ATTACHMENT_SELECTOR"]
        self.selectors["additional_id"] = self.source.parameter_values["ADDITIONAL_ID_SELECTOR"]

        self.web_driver_type = self.source.parameter_values["WEBDRIVER"]
        self.client_cert_directory = self.source.parameter_values["CLIENT_CERT_DIR"]

        set_proxy = False
        self.proxy = ""
        param_proxy = self.source.parameter_values["PROXY_SERVER"]
        if re.search(r"^(https?|socks[45])://", param_proxy.lower()):
            set_proxy = True
            self.proxy = param_proxy
        elif re.search(r"^.*:\d+$/", param_proxy.lower()):
            set_proxy = True
            self.proxy = f"http://{param_proxy}"

        if set_proxy:
            results = re.match(r"(https?)://([^/]+)/?$", self.proxy)
            if results:
                self.proxy_port = 8080
                self.proxy_proto = results.group(1)
                self.proxy_host = results.group(2)
            results = re.match(r"(https?)://([^/]+):(\d+)/?$", self.proxy)
            if results:
                self.proxy_proto = results.group(1)
                self.proxy_host = results.group(2)
                self.proxy_port = results.group(3)

        return True

    def __get_headless_driver_chrome(self):
        """Initialize and return Chrome driver.

        Returns:
            WebDriver: The initialized Chrome driver.
        """
        logger.debug("Initializing Chrome driver...")

        chrome_driver_executable = os.environ.get("SELENIUM_CHROME_DRIVER_PATH", "/usr/bin/chromedriver")

        chrome_options = ChromeOptions()
        chrome_options.page_load_strategy = "normal"  # .get() returns on document ready
        chrome_options.add_argument("start-maximized")
        chrome_options.add_argument("disable-infobars")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--incognito")
        chrome_service = ChromeService(executable_path=chrome_driver_executable)
        if self.user_agent:
            chrome_options.add_argument("user-agent=" + self.user_agent)
        if self.tor_service.lower() == "yes":
            socks_proxy = "socks5://127.0.0.1:9050"
            chrome_options.add_argument(f"--proxy-server={socks_proxy}")
        elif self.proxy:
            webdriver.DesiredCapabilities.CHROME["proxy"] = {
                "proxyType": "manual",
                "httpProxy": self.proxy,
                "ftpProxy": self.proxy,
                "sslProxy": self.proxy,
            }

        driver = webdriver.Chrome(service=chrome_service, options=chrome_options)
        logger.debug("Chrome driver initialized.")
        return driver

    def __get_headless_driver_firefox(self):
        """Initialize and return Firefox driver.

        Returns:
            WebDriver: The initialized Firefox driver.
        """
        logger.debug("Initializing Firefox driver...")

        firefox_driver_executable = os.environ.get("SELENIUM_FIREFOX_DRIVER_PATH", "/usr/local/bin/geckodriver")

        core_url = os.environ.get("TARANIS_NG_CORE_URL", "http://core")
        core_url_host = urlparse(core_url).hostname  # get only the hostname from URL

        firefox_options = FirefoxOptions()
        firefox_options.page_load_strategy = "normal"  # .get() returns on document ready
        firefox_options.add_argument("--headless")
        firefox_options.add_argument("--ignore-certificate-errors")
        firefox_options.add_argument("--incognito")

        if self.user_agent:
            firefox_options.add_argument(f"user-agent={self.user_agent}")

        if self.tor_service.lower() == "yes":
            firefox_options.set_preference("network.proxy.type", 1)  # manual proxy config
            firefox_options.set_preference("network.proxy.socks", "127.0.0.1")
            firefox_options.set_preference("network.proxy.socks_port", 9050)
            firefox_options.set_preference("network.proxy.no_proxies_on", f"localhost, ::1, 127.0.0.1, {core_url_host}, 127.0.0.0/8")

        elif self.proxy:
            firefox_options.set_preference("network.proxy.type", 1)  # manual proxy config
            firefox_options.set_preference("network.proxy.http", self.proxy_host)
            firefox_options.set_preference("network.proxy.http_port", int(self.proxy_port))
            firefox_options.set_preference("network.proxy.ssl", self.proxy_host)
            firefox_options.set_preference("network.proxy.ssl_port", int(self.proxy_port))
            firefox_options.set_preference("network.proxy.ftp", self.proxy)
            firefox_options.set_preference("network.proxy.ftp_port", int(self.proxy_port))
            firefox_options.set_preference("network.proxy.no_proxies_on", f"localhost, ::1, 127.0.0.1, {core_url_host}, 127.0.0.0/8")
        else:
            firefox_options.set_preference("network.proxy.type", 0)  # no proxy

        firefox_service = FirefoxService(executable_path=firefox_driver_executable)
        driver = webdriver.Firefox(service=firefox_service, options=firefox_options)

        logger.debug("Firefox driver initialized.")
        return driver

    def __get_headless_driver(self):
        """Initialize and return a headless browser driver.

        Returns:
            browser: The headless browser driver
        """
        try:
            if self.web_driver_type.lower() == "firefox":
                browser = self.__get_headless_driver_firefox()
            else:
                browser = self.__get_headless_driver_chrome()
            browser.implicitly_wait(15)  # how long to wait for elements when selector doesn't match
            return browser
        except Exception as error:
            logger.exception(f"{self.collector_source} Get headless driver failed: {error}")
            return None

    def __dispose_of_headless_driver(self, driver):
        """Destroy the headless browser driver, and its browser.

        Parameters:
            driver: The headless browser driver to be disposed of.
        """
        try:
            driver.quit()
        except Exception as error:
            logger.exception(f"{self.collector_source} Could not quit the headless browser driver: {error}")

    def __run_tor(self):
        """Run The Onion Router service in a subprocess."""
        logger.info(f"{self.collector_source} Initializing TOR")
        subprocess.Popen(["tor"])
        time.sleep(3)

    @BaseCollector.ignore_exceptions
    def collect(self, source):
        """Collect news items from this source (main function).

        Parameters:
            source (Source): The source to collect news items from.
        """
        self.source = source
        self.__parse_settings()
        self.news_items = []

        if self.tor_service.lower() == "yes":
            self.__run_tor()

        if self.interpret_as == "uri":
            result, message, total_processed_articles, total_failed_articles = self.__browse_title_page(self.web_url)

        elif self.interpret_as == "directory":
            logger.info(f"{self.collector_source} Searching for html files in {self.web_url}")
            for file_name in os.listdir(self.web_url):
                if file_name.lower().endswith(".html"):
                    html_file = f"file://{self.web_url}/{file_name}"
                    result, message = self.__browse_title_page(html_file)

    def __browse_title_page(self, index_url):
        """Spawn a browser, download the title page for parsing, call parser.

        Parameters:
            index_url (str): The URL of the title page.
        """
        browser = self.__get_headless_driver()
        if browser is None:
            logger.error(f"{self.collector_source} Error initializing the headless browser")
            return False, "Error initializing the headless browser", 0, 0

        logger.info(f"{self.collector_source} Requesting title page: {self.web_url}")
        try:
            browser.get(index_url)
        except Exception as error:
            logger.exception(f"{self.collector_source} Obtaining title page failed: {error}")
            self.__dispose_of_headless_driver(browser)
            return False, "Error obtaining title page", 0, 0

        # if there is a popup selector, click on it!
        if self.selectors["popup_close"]:
            popup = None
            try:
                popup = WebDriverWait(browser, 10).until(
                    EC.presence_of_element_located(self.__get_element_locator(self.selectors["popup_close"]))
                )
            except Exception as error:
                logger.exception(f"{self.collector_source} Popup find failed: {error}")
            if popup is not None:
                try:
                    popup.click()
                except Exception as error:
                    logger.exception(f"{self.collector_source} Popup click failed: {error}")

        # if there is a "load more" selector, click on it!
        page = 1
        while self.selectors["load_more"] and page < self.pagination_limit:
            try:
                load_more = WebDriverWait(browser, 5).until(
                    EC.element_to_be_clickable(self.__get_element_locator(self.selectors["load_more"]))
                )
                # TODO: check for None

                try:
                    action = ActionChains(browser)
                    action.move_to_element(load_more)
                    load_more.click()
                except Exception:
                    browser.execute_script("arguments[0].scrollIntoView(true);", load_more)
                    load_more.click()

                try:
                    WebDriverWait(browser, 5).until(EC.staleness_of(load_more))
                except Exception:
                    pass

            except Exception:
                break
            page += 1

        title_page_handle = browser.current_window_handle
        total_processed_articles, total_failed_articles = 0, 0
        while True:
            try:
                processed_articles, failed_articles = self.__process_title_page_articles(browser, title_page_handle, index_url)

                total_processed_articles += processed_articles
                total_failed_articles += failed_articles

                # safety cleanup
                if not self.__close_other_tabs(browser, title_page_handle, fallback_url=index_url):
                    logger.error(f"{self.collector_source} Page crawl failed (after-crawl clean up)")
                    break
            except Exception as error:
                logger.exception(f"{self.collector_source} Page crawl failed: {error}")
                break

            if page >= self.pagination_limit or not self.selectors["next_page"]:
                if self.pagination_limit > 1:
                    logger.info(f"{self.collector_source} Page limit reached")
                break

            # visit next page of results
            page += 1
            logger.info(f"{self.collector_source} Clicking 'next page'")
            try:
                next_page = self.__find_element_by(browser, self.selectors["next_page"])
                # TODO: check for None
                ActionChains(browser).move_to_element(next_page).click(next_page).perform()
            except Exception:
                logger.info(f"{self.collector_source} This was the last page")
                break

        self.__dispose_of_headless_driver(browser)
        BaseCollector.publish(self.news_items, self.source, self.collector_source)

        return True, "", total_processed_articles, total_failed_articles

    def __process_title_page_articles(self, browser, title_page_handle, index_url):
        """Parse the title page for articles.

        Parameters:
            browser (WebDriver): The browser instance.
            title_page_handle (str): The handle of the title page tab.
            index_url (str): The URL of the title page.
        Returns:
            (processed_articles, failed_articles) (tuple): A tuple containing the number of processed articles and
                the number of failed articles.
        """
        processed_articles, failed_articles = 0, 0
        article_items = self.__safe_find_elements_by(browser, self.selectors["single_article_link"])
        if article_items is None:
            logger.warning(f"{self.collector_source} Invalid page or incorrect selector for article items")
            return 0, 0

        index_url_just_before_click = browser.current_url

        count = 0
        # print(browser.page_source, flush=True)
        for item in article_items:
            count += 1
            # try:
            #     print("H: {0} {1:.200}".format(count, item.get_attribute('outerHTML')), flush=True)
            # except Exception as ex:
            #     pass
            # if first item works but next items have problems - it's because this:
            # https://www.selenium.dev/documentation/webdriver/troubleshooting/errors/#stale-element-reference-exception
            link = None
            try:
                link = item.get_attribute("href")
                if link is None:  # don't continue, it will crash in current situation
                    logger.warning(f"{self.collector_source} No link for article {count}/{len(article_items)}")
                    continue
                logger.info(f"{self.collector_source} Visiting article {count}/{len(article_items)}: {link}")
            except Exception:
                logger.warning(f"{self.collector_source} Failed to get link for article {count}/{len(article_items)}")
                continue

            click_method = 1  # TODO: some day, make this user-configurable with tri-state enum
            if click_method == 1:
                browser.switch_to.new_window("tab")
                browser.get(link)
            elif click_method == 2:
                browser.move_to_element(item)
                ActionChains(browser).key_down(Keys.CONTROL).click(item).key_up(Keys.CONTROL).perform()
                self.__wait_for_new_tab(browser, 15, title_page_handle)
            elif click_method == 3:
                browser.move_to_element(item)
                item.send_keys(Keys.CONTROL + Keys.RETURN)
                self.__wait_for_new_tab(browser, 15, title_page_handle)
            time.sleep(1)

            try:
                news_item = self.__process_article_page(index_url, browser)
                if news_item:
                    logger.debug(f"{self.collector_source} ... Title    : {news_item.title}")
                    logger.debug(
                        f"{self.collector_source} ... Review   : {news_item.review.replace('\r', '').replace('\n', ' ').strip()[:100]}"
                    )
                    logger.debug(
                        f"{self.collector_source} ... Content  : {news_item.content.replace('\r', '').replace('\n', ' ').strip()[:100]}"
                    )
                    logger.debug(f"{self.collector_source} ... Published: {news_item.published}")
                    self.news_items.append(news_item)
                else:
                    logger.warning(f"{self.collector_source} Parsing an article failed")
            except Exception as error:
                logger.exception(f"{self.collector_source} Parsing an article failed: {error}")

            if len(browser.window_handles) == 1:
                back_clicks = 1
                while browser.current_url != index_url_just_before_click:
                    browser.back()
                    back_clicks += 1
                    if back_clicks > 3:
                        logger.warning(f"{self.collector_source} Error during page crawl (cannot restore window after crawl)")
            elif not self.__close_other_tabs(browser, title_page_handle, fallback_url=index_url):
                logger.warning(f"{self.collector_source} Error during page crawl (after-crawl clean up)")
                break
            if count >= self.links_limit & self.links_limit > 0:
                logger.debug(f"{self.collector_source} Limit for article links reached ({self.links_limit})")
                break

        return processed_articles, failed_articles

    def __process_article_page(self, index_url, browser):
        """Parse a single article.

        Parameters:
            index_url (str): The URL of the title page.
            browser (WebDriver): The browser instance.
        Returns:
            news_item (NewsItemData): The parsed news item.
        """
        current_url = browser.current_url

        title = self.__find_element_text_by(browser, self.selectors["title"])

        article_full_text = self.__find_element_text_by(browser, self.selectors["article_full_text"])
        if self.word_limit > 0:
            article_full_text = " ".join(re.compile(r"\s+").split(article_full_text)[: self.word_limit])

        if self.selectors["article_description"]:
            article_description = self.__find_element_text_by(browser, self.selectors["article_description"])
        else:
            article_description = ""
        if self.word_limit > 0:
            article_description = " ".join(re.compile(r"\s+").split(article_description)[: self.word_limit])
        if not article_description:
            article_description = self.__smart_truncate(article_full_text)

        extracted_date = None
        published_str = self.__find_element_text_by(browser, self.selectors["published"])
        if published_str:
            extracted_date = parse(published_str, fuzzy=True)
        now = datetime.datetime.now()
        if extracted_date:
            published_str = extracted_date.strftime("%d.%m.%Y - %H:%M")
        else:
            published_str = now.strftime("%d.%m.%Y - %H:%M")

        link = current_url

        author = self.__find_element_text_by(browser, self.selectors["author"])

        for_hash = author + title + article_description
        news_item = NewsItemData(
            uuid.uuid4(),
            hashlib.sha256(for_hash.encode()).hexdigest(),
            title,
            article_description,
            self.web_url,
            link,
            published_str,
            author,
            now,
            article_full_text,
            self.source.id,
            [],
        )

        if self.selectors["additional_id"]:
            value = self.__find_element_text_by(browser, self.selectors["additional_id"])
            if value:
                key = "Additional_ID"
                binary_mime_type = ""
                binary_value = ""
                attribute = NewsItemAttribute(key, value, binary_mime_type, binary_value)
                news_item.attributes.append(attribute)
        return news_item
