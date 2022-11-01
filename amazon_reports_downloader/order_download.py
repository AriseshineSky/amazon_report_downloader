class OrderDownload():
    def go_to_today_orders_download_page(self):
        try:
            # 移动鼠标到reports
            for i in range(0, 3):
                click = 'false'
                try:
                    reports = WebDriverWait(self.driver, 20, 0.5).until(
                        EC.presence_of_element_located((By.ID, 'sc-navtab-reports')))
                    time.sleep(random.randint(4, 7))
                    webdriver.ActionChains(self.driver).move_to_element(reports).perform()
                    logger.info('go to reports')
                    js_change_display = 'document.querySelector("#sc-navtab-reports > ul").style.display = "block";'
                    js_change_opacity = 'document.querySelector("#sc-navtab-reports > ul").style.opacity = 1;'
                    self.driver.execute_script(js_change_display)
                    self.driver.execute_script(js_change_opacity)
                    # click fulfillments
                    try:
                        logger.info('click fulfillments')
                        fulfillment_link = self.driver.find_element_by_xpath(
                            '//*[@id="sc-navtab-reports"]/ul/li/a[contains(text(), "Fulfil")]').get_attribute('href')
                        self.driver.get(fulfillment_link)
                        break
                    except Exception as e:
                        print(e)

                    # length = len(self.driver.find_elements_by_xpath('//*[@id="sc-navtab-reports"]/ul/li'))
                    # logger.info(length)
                    # for i in range(1, length):
                    #     logger.info(('//*[@id="sc-navtab-reports"]/ul/li[{}]'.format(i)))
                    #     report_name = self.driver.find_element_by_xpath(
                    #         '//*[@id="sc-navtab-reports"]/ul/li[{}]'.format(i)).text.strip()
                    #     logger.info(report_name)
                    #     if report_name.startswith('Fulfil'):
                    #         time.sleep(random.randint(3, 7))
                    #         js_click_fulfillments = "document.querySelector('#sc-navtab-reports > ul > li:nth-child({}) > a').click();".format(
                    #             i)
                    #         self.driver.execute_script(js_click_fulfillments)
                    #         logger.info('click fulfillments')
                    #         time.sleep(random.randint(1, 7))
                    #         click = 'true'
                    #         break
                    # if click == 'true':
                    #     break
                except Exception as e:
                    print(e)

            # click all orders

            try:
                WebDriverWait(self.driver, 20, 0.5).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="sc-sidepanel"]/div/ul[3]/li[10]/a'))).click()
                time.sleep(random.randint(1, 7))
            except Exception as e:
                print(e)

            js_click_all_orders = "document.querySelector('#FlatFileAllOrdersReport > a').click();"
            self.driver.execute_script(js_click_all_orders)

            logger.info('click all orders')
            time.sleep(random.randint(1, 7))

            # click order date drop down

            WebDriverWait(self.driver, 20, 0.5).until(EC.presence_of_element_located((By.ID, 'eventDateType'))).click()

            time.sleep(random.randint(1, 7))

            # select Last Updated Date

            WebDriverWait(self.driver, 20, 0.5).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="eventDateType"]/select/option[2]'))).click()

            logger.info('choose Last Updated Date')
            time.sleep(random.randint(1, 7))

            # click last date drop down

            WebDriverWait(self.driver, 20, 0.5).until(
                EC.presence_of_element_located((By.ID, 'downloadDateDropdown'))).click()

            time.sleep(random.randint(1, 7))

            # select Exact Date

            WebDriverWait(self.driver, 20, 0.5).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="downloadDateDropdown"]/option[6]'))).click()

            time.sleep(random.randint(1, 7))

            # From today to today

            from_elem = WebDriverWait(self.driver, 40, 0.5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '#fromDateDownload')))
            # today = datetime.datetime.today().strftime("%m/%d/%Y")
            today = datetime.utcnow().replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=-7))).strftime("%m/%d/%Y")
            time.sleep(random.randint(1, 7))
            for i in range(0, 30):
                from_elem.send_keys('\b')
            from_elem.send_keys(today)
            logger.info(from_elem.get_attribute('value'))
            time.sleep(random.randint(3, 7))
            to_elem = WebDriverWait(self.driver, 40, 0.5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '#toDateDownload')))
            for i in range(0, 30):
                to_elem.send_keys('\b')
            time.sleep(random.randint(1, 7))
            to_elem.send_keys(today)

            logger.info('select today')
            time.sleep(random.randint(4, 7))

            # click download

            WebDriverWait(self.driver, 120, 0.5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '#requestDownload button')))
            download_button = "document.querySelector('#requestDownload button').click();"
            self.driver.execute_script(download_button)

            logger.info('download request')

            time.sleep(random.randint(10, 20))
            WebDriverWait(self.driver, 120, 0.5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '#downloadArchive table tbody tr:first-child a')))
            download_button = self.driver.find_element_by_css_selector('#downloadArchive table tbody tr:first-child a')
            # download_button = WebDriverWait(self.driver, 40, 0.5).until(EC.presence_of_element_located((By.XPATH, '//*[@id="downloadArchive"]/table/tbody/tr[1]/td[4]/a')))
            logger.info("download_button")

            download_link = download_button.get_attribute("href")

            logger.info(download_link)
            self.driver.get(download_link)
            logger.info('downloading')
            orders_name = re.findall(r"GET_FLAT_FILE_ALL_ORDERS_DATA_BY_LAST_UPDATE__(\d*)\.txt", download_link)[0]
            logger.info(orders_name)
            return orders_name + '.txt'

        except Exception as e:
            self.save_page(traceback.format_exc())
            print(e)
            self.driver.quit()